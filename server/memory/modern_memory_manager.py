"""
现代化记忆管理器
整合所有记忆系统组件的统一管理接口
"""
import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from utils.logger import app_logger
from memory.qdrant_manager import qdrant_manager
from memory.redis_manager import redis_manager
from memory.importance_calculator import importance_calculator
from memory.compression_service import compression_service
from memory.profile_service import profile_service
from memory.semantic_search import semantic_search_service
from memory.embedding import EmbeddingService
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class ModernMemoryManager:
    """现代化记忆管理器"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.db_manager = DatabaseManager()
        
        # 记忆配置
        self.short_term_threshold = 1000  # tokens
        self.long_term_threshold = 0.6    # importance score
        self.max_recent_turns = 3
        
        # 异步任务队列
        self.background_tasks = set()
        
        app_logger.info("ModernMemoryManager initialized")
    
    async def process_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """
        处理对话，更新记忆系统
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            message: 用户消息
            response: 助手回复
            intent: 对话意图
            sources: 信息来源
            
        Returns:
            处理结果
        """
        try:
            # 1. 计算重要性评分
            importance_score = importance_calculator.calculate_conversation_importance(
                message=message,
                response=response,
                intent=intent,
                user_id=user_id,
                conversation_context={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "turn_count": await self._get_conversation_turn_count(conversation_id)
                }
            )
            
            # 2. 异步更新记忆（不阻塞主流程）
            asyncio.create_task(self._update_memories_async(
                user_id, conversation_id, message, response, intent, sources, importance_score
            ))
            
            # 3. 返回处理结果
            return {
                "success": True,
                "importance_score": importance_score,
                "should_store_long_term": importance_calculator.should_store_in_long_term(importance_score),
                "message": "Memory processing initiated"
            }
            
        except Exception as e:
            app_logger.error(f"处理对话失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Memory processing failed"
            }
    
    async def _update_memories_async(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str],
        importance_score: float
    ):
        """异步更新记忆"""
        try:
            # 1. 提取用户偏好
            await profile_service.extract_user_preferences(
                user_id=user_id,
                message=message,
                conversation_context={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "turn_count": await self._get_conversation_turn_count(conversation_id)
                }
            )
            
            # 2. 存储到长期记忆（如果重要性足够）
            if importance_score >= self.long_term_threshold:
                await self._store_long_term_memory(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=message,
                    response=response,
                    intent=intent,
                    sources=sources or [],
                    importance_score=importance_score
                )
            
            # 3. 更新记忆索引
            await self._update_memory_index(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type="semantic" if importance_score >= self.long_term_threshold else "short",
                importance_score=importance_score,
                content_preview=message[:100] + "..." if len(message) > 100 else message
            )
            
            app_logger.info(f"记忆更新完成: 用户={user_id}, 对话={conversation_id}, 重要性={importance_score:.2f}")
            
        except Exception as e:
            app_logger.error(f"异步更新记忆失败: {e}")
    
    async def _store_long_term_memory(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str],
        importance_score: float
    ):
        """存储到长期记忆"""
        try:
            # 构建记忆内容
            memory_content = f"问题：{message}\n回答：{response[:300]}{'...' if len(response) > 300 else ''}"
            
            # 生成嵌入向量
            embedding = await self.embedding_service.embed_text(memory_content)
            if not embedding:
                app_logger.error("Failed to generate embedding for long-term memory")
                return False
            
            # 存储到Qdrant
            memory_id = await qdrant_manager.add_semantic_memory(
                content=memory_content,
                embedding=embedding,
                user_id=user_id,
                conversation_id=conversation_id,
                importance_score=importance_score,
                metadata={
                    "intent": intent,
                    "sources": sources,
                    "message_length": len(message),
                    "response_length": len(response)
                }
            )
            
            if memory_id:
                app_logger.info(f"长期记忆存储成功: {memory_id}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"存储长期记忆失败: {e}")
            return False
    
    async def _update_memory_index(
        self,
        user_id: str,
        conversation_id: str,
        memory_type: str,
        importance_score: float,
        content_preview: str
    ):
        """更新记忆索引"""
        try:
            memory_id = str(uuid.uuid4())
            
            # 存储到数据库
            query = """
                INSERT INTO memory_index 
                (id, user_id, memory_type, importance_score, content_preview, created_at, last_accessed, access_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            metadata = {
                "conversation_id": conversation_id,
                "created_at": datetime.now().isoformat()
            }
            
            self.db_manager.execute_update(
                query,
                (
                    memory_id,
                    user_id,
                    memory_type,
                    importance_score,
                    content_preview,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    0,
                    str(metadata)
                )
            )
            
            # 存储到Redis索引
            await redis_manager.set_memory_index(
                memory_id=memory_id,
                index_data={
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "importance_score": importance_score,
                    "conversation_id": conversation_id,
                    "created_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            app_logger.error(f"更新记忆索引失败: {e}")
    
    async def get_conversation_context(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        limit: int = 5
    ) -> Tuple[str, Dict[str, Any]]:
        """
        获取对话上下文
        
        Returns:
            (context_text, metadata)
        """
        try:
            context_parts = []
            metadata = {
                "short_term_compressed": False,
                "long_term_found": 0,
                "user_profile_used": False
            }
            
            # 1. 获取短期记忆（最近对话）
            short_term_context, short_metadata = await self._get_short_term_context(
                conversation_id, limit
            )
            if short_term_context:
                context_parts.append(short_term_context)
                metadata.update(short_metadata)
            
            # 2. 获取长期记忆（语义搜索）
            long_term_context, long_term_count = await self._get_long_term_context(
                user_id, current_message, limit
            )
            if long_term_context:
                context_parts.append(long_term_context)
                metadata["long_term_found"] = long_term_count
            
            # 3. 获取用户画像上下文
            profile_context = await profile_service.build_contextual_prompt(
                user_id, current_message
            )
            if profile_context:
                context_parts.append(profile_context)
                metadata["user_profile_used"] = True
            
            # 合并上下文
            full_context = "\n\n".join(context_parts)
            
            app_logger.info(
                f"上下文获取完成: 用户={user_id}, 对话={conversation_id}, "
                f"短期压缩={metadata.get('short_term_compressed', False)}, "
                f"长期记忆={metadata.get('long_term_found', 0)}条"
            )
            
            return full_context, metadata
            
        except Exception as e:
            app_logger.error(f"获取对话上下文失败: {e}")
            return "", {"error": str(e)}
    
    async def _get_short_term_context(
        self,
        conversation_id: str,
        limit: int
    ) -> Tuple[str, Dict[str, Any]]:
        """获取短期记忆上下文"""
        try:
            # 从数据库获取最近消息
            query = """
                SELECT role, content, created_at
                FROM messages 
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            
            messages = self.db_manager.execute_query(query, (conversation_id, limit * 2))
            messages.reverse()  # 按时间正序排列
            
            if not messages:
                return "", {"total_messages": 0, "compressed": False}
            
            # 使用压缩服务处理
            formatted_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            compressed_context, compression_metadata = await compression_service.compress_conversation(
                conversation_id=conversation_id,
                messages=formatted_messages
            )
            
            return compressed_context, compression_metadata
            
        except Exception as e:
            app_logger.error(f"获取短期记忆上下文失败: {e}")
            return "", {"error": str(e)}
    
    async def _get_long_term_context(
        self,
        user_id: str,
        current_message: str,
        limit: int
    ) -> Tuple[str, int]:
        """获取长期记忆上下文"""
        try:
            # 搜索相关记忆
            memories = await semantic_search_service.search_semantic_memories(
                query=current_message,
                user_id=user_id,
                limit=limit
            )
            
            if not memories:
                return "", 0
            
            # 构建上下文
            context_parts = ["【相关历史对话】"]
            for i, memory in enumerate(memories, 1):
                content = memory.get("content", "")
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    context_parts.append(f"{i}. {preview}")
            
            return "\n".join(context_parts), len(memories)
            
        except Exception as e:
            app_logger.error(f"获取长期记忆上下文失败: {e}")
            return "", 0
    
    async def search_memories(
        self,
        query: str,
        user_id: str,
        memory_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            results = await semantic_search_service.search_semantic_memories(
                query=query,
                user_id=user_id,
                limit=limit,
                memory_types=memory_types
            )
            
            return results
            
        except Exception as e:
            app_logger.error(f"搜索记忆失败: {e}")
            return []
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """获取用户洞察"""
        try:
            # 获取用户画像洞察
            profile_insights = await profile_service.get_user_insights(user_id)
            
            # 获取记忆统计
            memory_stats = await redis_manager.get_user_memory_stats(user_id)
            
            # 获取记忆时间线
            memory_timeline = await semantic_search_service.get_memory_timeline(
                user_id=user_id,
                days=30,
                limit=10
            )
            
            return {
                "profile_insights": profile_insights,
                "memory_stats": memory_stats,
                "recent_memories": memory_timeline,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            app_logger.error(f"获取用户洞察失败: {e}")
            return {}
    
    async def _get_conversation_turn_count(self, conversation_id: str) -> int:
        """获取对话轮数"""
        try:
            query = "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?"
            result = self.db_manager.execute_query(query, (conversation_id,))
            return result[0]["count"] if result else 0
        except Exception as e:
            app_logger.error(f"获取对话轮数失败: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查各个组件
            qdrant_health = await qdrant_manager.health_check()
            redis_health = await redis_manager.health_check()
            embedding_health = await self.embedding_service.health_check()
            search_health = await semantic_search_service.health_check()
            
            overall_status = "ok"
            if any(comp["status"] != "ok" for comp in [qdrant_health, redis_health, embedding_health, search_health]):
                overall_status = "error"
            
            return {
                "status": overall_status,
                "components": {
                    "qdrant": qdrant_health,
                    "redis": redis_health,
                    "embedding": embedding_health,
                    "semantic_search": search_health
                },
                "config": {
                    "short_term_threshold": self.short_term_threshold,
                    "long_term_threshold": self.long_term_threshold,
                    "max_recent_turns": self.max_recent_turns
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Memory manager health check failed: {e}"
            }
    
    async def cleanup_old_memories(self, days: int = 30):
        """清理旧记忆"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 清理数据库中的旧记忆索引
            query = "DELETE FROM memory_index WHERE created_at < ? AND importance_score < 0.3"
            deleted_count = self.db_manager.execute_update(query, (cutoff_date.isoformat(),))
            
            # 清理Redis缓存
            await redis_manager.clear_user_data("temp_cleanup")
            
            app_logger.info(f"清理完成: 删除了 {deleted_count} 条旧记忆")
            return deleted_count
            
        except Exception as e:
            app_logger.error(f"清理旧记忆失败: {e}")
            return 0


# 全局实例
modern_memory_manager = ModernMemoryManager()

