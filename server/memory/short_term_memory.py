"""
短期记忆模块（重构版）
负责管理对话历史、压缩和最近的上下文
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from utils.logger import app_logger, log_execution_time
from memory.redis_manager import redis_manager
from memory.memory_formatter import memory_formatter
from memory.memory_compression import memory_compressor
from memory.summary_generator import summary_generator
from config.settings import settings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期记忆管理器（重构版 - 职责更清晰，代码更简洁）"""
    
    def __init__(self, enabled: bool = None):
        # 从配置文件读取启用状态
        self.enabled = enabled if enabled is not None else settings.short_term_memory_enabled
        self.redis_manager = redis_manager
        self.formatter = memory_formatter
        self.compressor = memory_compressor
        self.summary_gen = summary_generator
        
        # 短期记忆配置
        self.max_tokens = 3000  # 3k token阈值
        self.warning_tokens = 2500  # 警告阈值
        self.max_recent_turns = 3  # 保留最近3轮对话
        
        app_logger.info(f"ShortTermMemory initialized - enabled: {self.enabled}")
    
    async def _ensure_compression_processor_started(self) -> None:
        """确保压缩处理器已启动"""
        if self.enabled:
            await self.compressor.ensure_processor_started()
    
    @log_execution_time(log_args=True)
    async def get_recent_context(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """获取最近的对话上下文：Redis优先，DB回退"""
        if not self.enabled:
            app_logger.info(f"🔍 [SHORT-TERM] Memory disabled for {user_id}:{conversation_id}")
            return {
                "context": "",
                "metadata": {
                    "enabled": False,
                    "reason": "Short-term memory disabled"
                }
            }
        
        try:
            app_logger.info(f"🔍 [SHORT-TERM] Getting context for {user_id}:{conversation_id} (limit={limit})")
            
            # 1. 优先从Redis获取短期记忆
            redis_context = await self._get_from_redis(user_id, conversation_id, limit)
            conversations = await self.redis_manager.get_recent_conversations(user_id, conversation_id, limit)
            
            if redis_context:
                # Redis中有数据，直接返回
                app_logger.info(f"📝 [SHORT-TERM] Retrieved from Redis for {user_id}:{conversation_id}")
                app_logger.info(f"📄 [SHORT-TERM] Context content: {redis_context[:200]}...")
                return {
                    "context": redis_context,
                    "metadata": {
                        "enabled": True,
                        "source": "redis",
                        "limit": limit,
                        "conversations": conversations  # 包含原始对话数据用于意图识别
                    }
                }
            
            # 2. Redis中没有数据，从数据库获取并存储到Redis
            from database import conversation_repo
            
            messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=limit
            )
            
            if not messages:
                app_logger.info(f"ℹ️ [SHORT-TERM] No messages found in DB for {user_id}:{conversation_id}")
                return {
                    "context": "",
                    "metadata": {
                        "enabled": True,
                        "source": "empty",
                        "limit": limit,
                        "conversations": []
                    }
                }
            
            # 3. 格式化消息
            formatted_context = self.formatter.format_recent_messages(messages)
            
            # 4. 存储到Redis以备后用
            for msg in messages:
                await self.redis_manager.store_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=msg.get('user_message', ''),
                    response=msg.get('ai_response', ''),
                    metadata={}
                )
            
            app_logger.info(f"📝 [SHORT-TERM] Retrieved from DB and cached to Redis for {user_id}:{conversation_id}")
            app_logger.info(f"📄 [SHORT-TERM] Context content: {formatted_context[:200]}...")
            
            # 5. 获取总结上下文
            summarized_context = await self._get_summarized_context(user_id, conversation_id)
            
            # 6. 组合最终上下文
            final_context = formatted_context
            if summarized_context:
                final_context = f"{summarized_context}\n\n{formatted_context}"
            
            return {
                "context": final_context,
                "metadata": {
                    "enabled": True,
                    "source": "database",
                    "limit": limit,
                    "conversations": conversations or messages,
                    "has_summary": bool(summarized_context)
                }
            }
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to get context: {e}")
            return {
                "context": "",
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    async def store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """存储单轮对话到短期记忆"""
        if not self.enabled:
            return False
        
        try:
            await self.redis_manager.store_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                response=response,
                metadata=metadata or {}
            )
            return True
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to store conversation: {e}")
            return False
    
    async def smart_store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """智能存储对话：使用异步压缩和递增总结"""
        if not self.enabled:
            return False
        
        try:
            # 1. 存储到Redis
            stored = await self.store_conversation(
                user_id, conversation_id, message, response, metadata
            )
            
            if not stored:
                return False
            
            # 2. 确保压缩处理器已启动
            await self._ensure_compression_processor_started()
            
            # 3. 检查是否需要压缩
            from database import conversation_repo
            all_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            # 计算token数
            total_tokens = self.formatter.count_tokens_for_messages(all_messages)
            
            # 4. 根据token数决定是否需要压缩
            if total_tokens >= self.max_tokens:
                # 超过阈值，高优先级压缩
                await self.compressor.queue_compression_task(
                    user_id, conversation_id, priority='high'
                )
                app_logger.info(f"🚨 [SHORT-TERM] Token limit exceeded ({total_tokens}/{self.max_tokens}), queued high priority compression")
            
            elif total_tokens >= self.warning_tokens:
                # 接近阈值，普通优先级压缩
                await self.compressor.queue_compression_task(
                    user_id, conversation_id, priority='normal'
                )
                app_logger.info(f"⚠️ [SHORT-TERM] Token warning ({total_tokens}/{self.warning_tokens}), queued normal priority compression")
            
            return True
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Smart store conversation failed: {e}")
            return False
    
    async def store_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary: str
    ) -> bool:
        """存储对话摘要到Redis"""
        try:
            summary_key = f"conversation_summary:{user_id}:{conversation_id}"
            self.redis_manager.redis_conn.set(
                summary_key,
                summary,
                ex=86400 * 30  # 30天过期
            )
            app_logger.info(f"💾 [SHORT-TERM] Stored conversation summary for {user_id}:{conversation_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to store conversation summary: {e}")
            return False
    
    async def generate_and_store_summary(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """生成并存储对话摘要"""
        try:
            if len(messages) < 6:  # 少于3轮对话不需要摘要
                return False
            
            # 排除最近2轮对话，只总结更早的对话
            messages_to_summarize = messages[:-4]
            
            # 生成摘要
            summary = await self.summary_gen.generate_summary_for_messages(messages_to_summarize)
            
            if summary:
                # 存储摘要
                return await self.store_conversation_summary(user_id, conversation_id, summary)
            
            return False
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to generate and store summary: {e}")
            return False
    
    async def clear_user_data(self, user_id: str) -> bool:
        """清除用户的短期记忆数据"""
        if not self.enabled:
            return False
        
        try:
            await self.redis_manager.clear_user_data(user_id)
            app_logger.info(f"🗑️ [SHORT-TERM] Cleared data for user {user_id}")
            return True
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to clear user data: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Short-term memory is disabled",
                "components": {
                    "redis_manager": "disabled"
                }
            }
        
        try:
            # 检查Redis连接
            redis_health = await self.redis_manager.health_check()
            
            # 检查压缩器状态
            compression_status = {
                "processor_started": self.compressor._processor_started,
                "queue_size": len(self.compressor.compression_queue),
                "active_compressions": self.compressor.active_compressions
            }
            
            return {
                "status": "ok" if redis_health["status"] == "ok" else "error",
                "message": "Short-term memory is healthy" if redis_health["status"] == "ok" else "Redis connection failed",
                "components": {
                    "redis_manager": redis_health["status"],
                    "formatter": "ok",
                    "compressor": "ok" if self.compressor._processor_started else "not_started",
                    "summary_generator": "ok"
                },
                "config": {
                    "enabled": self.enabled,
                    "max_tokens": self.max_tokens,
                    "warning_tokens": self.warning_tokens,
                    "max_recent_turns": self.max_recent_turns
                },
                "compression_status": compression_status
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {e}",
                "components": {
                    "redis_manager": "error"
                }
            }
    
    # ===== 私有辅助方法 =====
    
    async def _get_from_redis(self, user_id: str, conversation_id: str, limit: int = 10) -> str:
        """从Redis获取最近的对话上下文"""
        try:
            # 获取最近的对话
            conversations = await self.redis_manager.get_recent_conversations(
                user_id, conversation_id, limit
            )
            
            if not conversations:
                return ""
            
            # 格式化对话
            formatted = self.formatter.format_conversations(conversations)
            
            # 获取摘要层
            layer_summaries = await self._get_layer_summaries(user_id, conversation_id)
            
            # 组合摘要和最近对话
            if layer_summaries:
                formatted = f"{layer_summaries}\n\n最近对话：\n{formatted}"
            
            return formatted
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to get from Redis: {e}")
            return ""
    
    async def _get_layer_summaries(
        self,
        user_id: str,
        conversation_id: str
    ) -> str:
        """获取分层摘要"""
        try:
            summaries = []
            for layer in ['L3', 'L2', 'L1']:  # 从大到小
                summary = await self.redis_manager.get_conversation_summary(
                    user_id, conversation_id, layer
                )
                if summary:
                    summaries.append(f"[{layer}摘要] {summary}")
            
            return "\n".join(summaries) if summaries else ""
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to get layer summaries: {e}")
            return ""
    
    async def _get_summarized_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> str:
        """获取更早对话的summarized信息"""
        try:
            # 从Redis获取当前对话的summarized信息
            summary_key = f"conversation_summary:{user_id}:{conversation_id}"
            summary = self.redis_manager.redis_conn.get(summary_key)
            
            if summary:
                # Redis返回的数据可能是字符串或字节，需要处理
                if isinstance(summary, bytes):
                    return summary.decode('utf-8')
                return str(summary)
            
            return ""
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to get summarized context: {e}")
            return ""


# 全局实例 - 从配置文件读取启用状态
short_term_memory = ShortTermMemory()
