"""
短期记忆模块
负责管理对话历史、压缩和最近的上下文
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from utils.logger import app_logger
from memory.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期记忆管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.redis_manager = redis_manager
        
        # 短期记忆配置
        self.max_tokens = 3000  # 3k token阈值
        self.max_recent_turns = 3  # 保留最近3轮对话
        
        app_logger.info(f"ShortTermMemory initialized - enabled: {enabled}")
    
    
    async def get_recent_context(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """获取最近的对话上下文：Redis优先，DB回退"""
        if not self.enabled:
            return {
                "context": "",
                "metadata": {
                    "enabled": False,
                    "reason": "Short-term memory disabled"
                }
            }
        
        try:
            # 1. 优先从Redis获取短期记忆
            redis_context = await self._get_from_redis(user_id, conversation_id)
            
            if redis_context:
                # Redis中有数据，直接返回
                return {
                    "context": redis_context,
                    "metadata": {
                        "enabled": True,
                        "source": "redis",
                        "limit": limit
                    }
                }
            
            # 2. Redis中没有数据，从数据库获取并存储到Redis
            from database import conversation_repo
            
            recent_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=limit
            )
            
            if not recent_messages:
                return {
                    "context": "",
                    "metadata": {
                        "enabled": True,
                        "source": "database",
                        "recent_turns": 0,
                        "limit": limit
                    }
                }
            
            # 3. 检查是否需要压缩
            total_tokens = self._count_tokens_for_messages(recent_messages)
            
            if total_tokens > self.max_tokens:
                # 超过3k token，需要压缩
                await self._compress_and_store(user_id, conversation_id, recent_messages)
                
                # 重新从Redis获取压缩后的数据
                redis_context = await self._get_from_redis(user_id, conversation_id)
                return {
                    "context": redis_context or "",
                    "metadata": {
                        "enabled": True,
                        "source": "redis_compressed",
                        "recent_turns": len(recent_messages),
                        "compressed": True,
                        "limit": limit
                    }
                }
            else:
                # 未超过3k token，直接存储到Redis
                for msg in recent_messages:
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                
                # 格式化并返回
                context = self._format_recent_messages(recent_messages)
                return {
                    "context": context,
                    "metadata": {
                        "enabled": True,
                        "source": "database_to_redis",
                        "recent_turns": len(recent_messages),
                        "compressed": False,
                        "limit": limit
                    }
                }
            
        except Exception as e:
            app_logger.error(f"Failed to get recent context: {e}")
            return {
                "context": "",
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    def _count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息的token数量"""
        total_text = ""
        for message in messages:
            total_text += message.get("content", "")
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    def _format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
        """格式化最近的消息"""
        if not messages:
            return ""
        
        formatted = []
        for msg in messages:
            user_msg = msg.get('user_message', '')
            ai_response = msg.get('ai_response', '')
            if user_msg and ai_response:
                formatted.append(f"User: {user_msg}")
                formatted.append(f"Assistant: {ai_response}")
                formatted.append("")  # 空行分隔
        
        return "\n".join(formatted)
    
    def _format_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not conversations:
            return ""
        
        formatted = []
        for conv in conversations:
            timestamp = conv.get("timestamp", "")
            message = conv.get("message", "")
            response = conv.get("response", "")
            
            formatted.append(f"[{timestamp}] 用户: {message}")
            formatted.append(f"[{timestamp}] 助手: {response}")
        
        return "\n".join(formatted)
    
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
            app_logger.error(f"Failed to store conversation: {e}")
            return False
    
    async def smart_store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """智能存储对话：根据token数量决定是否压缩"""
        if not self.enabled:
            return False
        
        try:
            # 获取当前对话的所有消息
            from database import conversation_repo
            all_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            # 计算总token数
            total_tokens = self._count_tokens_for_messages(all_messages + [
                {'user_message': message, 'ai_response': response}
            ])
            
            if total_tokens > self.max_tokens:
                # 超过3k token，需要压缩
                await self._compress_and_store(user_id, conversation_id, all_messages + [
                    {'user_message': message, 'ai_response': response}
                ])
            else:
                # 未超过3k token，直接存储
                await self.redis_manager.store_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=message,
                    response=response,
                    metadata=metadata or {}
                )
            
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to smart store conversation: {e}")
            return False
    
    async def clear_user_data(self, user_id: str) -> bool:
        """清理用户的短期记忆数据"""
        if not self.enabled:
            return True
        
        try:
            await self.redis_manager.clear_user_data(user_id)
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to clear user data: {e}")
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
            
            return {
                "status": "ok",
                "message": "Short-term memory is healthy",
                "components": {
                    "redis_manager": redis_health["status"]
                },
                "config": {
                    "max_tokens": self.max_tokens,
                    "max_recent_turns": self.max_recent_turns,
                    "enabled": self.enabled
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Short-term memory health check failed: {e}",
                "components": {
                    "redis_manager": "error"
                }
            }


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
            app_logger.error(f"Failed to get summarized context: {e}")
            return ""
    
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
            app_logger.info(f"Stored conversation summary for {user_id}:{conversation_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to store conversation summary: {e}")
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
            
            # 使用AI生成摘要
            from services.ai_service import ai_service
            
            # 构建对话文本
            conversation_text = ""
            for msg in messages[:-4]:  # 排除最近2轮对话
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    conversation_text += f"用户: {content}\n"
                elif role == 'assistant':
                    conversation_text += f"助手: {content}\n"
            
            if not conversation_text.strip():
                return False
            
            # 生成摘要
            summary_prompt = f"""请为以下对话生成一个简洁的摘要，保留关键信息和上下文：

{conversation_text}

摘要要求：
1. 用2-3句话概括对话的主要内容
2. 保留重要的用户需求和AI的回答要点
3. 使用中文，语言简洁明了

摘要："""
            
            summary = await ai_service.generate_response(summary_prompt)
            
            if summary and len(summary.strip()) > 10:
                return await self.store_conversation_summary(user_id, conversation_id, summary.strip())
            
            return False
            
        except Exception as e:
            app_logger.error(f"Failed to generate and store summary: {e}")
            return False
    
    def _count_tokens_for_messages(self, messages: List[Dict[str, Any]]) -> int:
        """计算消息列表的token数量"""
        total_text = ""
        for msg in messages:
            total_text += msg.get('user_message', '') + " " + msg.get('ai_response', '')
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    async def _compress_and_store(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """压缩并存储对话"""
        try:
            # 保留最近3轮对话
            recent_messages = messages[-self.max_recent_turns:] if len(messages) > self.max_recent_turns else messages
            old_messages = messages[:-self.max_recent_turns] if len(messages) > self.max_recent_turns else []
            
            if not old_messages:
                # 没有旧消息需要压缩，直接存储最近对话
                for msg in recent_messages:
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                return True
            
            # 生成旧消息的摘要
            summary = await self._generate_summary_for_messages(old_messages)
            
            if summary:
                # 存储摘要到Redis
                await self.store_conversation_summary(user_id, conversation_id, summary)
                
                # 存储最近3轮对话
                for msg in recent_messages:
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                
                app_logger.info(f"Compressed and stored conversation for {user_id}:{conversation_id}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"Failed to compress and store: {e}")
            return False
    
    async def _generate_summary_for_messages(self, messages: List[Dict[str, Any]]) -> str:
        """为消息列表生成摘要"""
        try:
            if not messages:
                return ""
            
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                conversation_text += f"用户: {msg.get('user_message', '')}\n"
                conversation_text += f"助手: {msg.get('ai_response', '')}\n"
            
            if not conversation_text.strip():
                return ""
            
            # 使用AI生成摘要
            from services.ai_service import ai_service
            
            summary_prompt = f"""请为以下对话生成一个简洁的摘要，保留关键信息和上下文：

{conversation_text}

摘要要求：
1. 用2-3句话概括对话的主要内容
2. 保留重要的用户需求和AI的回答要点
3. 使用中文，语言简洁明了

摘要："""
            
            summary = await ai_service.generate_response(summary_prompt)
            return summary.strip() if summary else ""
            
        except Exception as e:
            app_logger.error(f"Failed to generate summary for messages: {e}")
            return ""
    
    async def _get_from_redis(self, user_id: str, conversation_id: str) -> str:
        """从Redis获取短期记忆上下文"""
        try:
            # 获取Redis中的对话数据
            conversations = await self.redis_manager.get_recent_conversations(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=10
            )
            
            if not conversations:
                return ""
            
            # 获取摘要信息
            summarized_context = await self._get_summarized_context(user_id, conversation_id)
            
            # 组合上下文
            context_parts = []
            
            if summarized_context:
                context_parts.append(f"Earlier conversation summary:\n{summarized_context}")
            
            if conversations:
                recent_context = self._format_conversations(conversations)
                context_parts.append(f"Recent conversation:\n{recent_context}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            app_logger.error(f"Failed to get from Redis: {e}")
            return ""

# 全局实例 - 默认启用
short_term_memory = ShortTermMemory(enabled=True)
