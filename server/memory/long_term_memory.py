"""
长期记忆模块
负责管理语义记忆、用户画像、知识图谱等长期存储
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from utils.logger import app_logger
from memory.qdrant_manager import qdrant_manager
from memory.profile_service import profile_service
from memory.semantic_search import semantic_search_service
from memory.importance_calculator import importance_calculator
from memory.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class LongTermMemory:
    """长期记忆管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.qdrant_manager = qdrant_manager
        self.profile_service = profile_service
        self.semantic_search = semantic_search_service
        self.importance_calculator = importance_calculator
        self.embedding_service = EmbeddingService()
        
        # 长期记忆配置
        self.min_importance_score = 0.6
        self.max_memories_per_user = 1000
        self.memory_decay_days = 30
        
        app_logger.info(f"LongTermMemory initialized - enabled: {enabled}")
    
    async def process_conversation_for_storage(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """处理对话，决定是否存储到长期记忆"""
        if not self.enabled:
            return {
                "stored": False,
                "importance_score": 0.0,
                "reason": "Long-term memory disabled"
            }
        
        try:
            # 1. 计算重要性评分
            importance_score = self.importance_calculator.calculate_conversation_importance(
                message=message,
                response=response,
                intent=intent,
                user_id=user_id,
                conversation_context={
                    "user_id": user_id,
                    "turn_count": 1,
                    "sources": sources or []
                }
            )
            
            # 2. 判断是否应该存储
            should_store = importance_score >= self.min_importance_score
            
            if should_store:
                # 3. 提取用户画像信息
                await self._extract_user_profile(user_id, message, response)
                
                # 4. 存储到语义记忆
                memory_id = await self._store_semantic_memory(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message=message,
                    response=response,
                    importance_score=importance_score,
                    intent=intent,
                    sources=sources
                )
                
                return {
                    "stored": True,
                    "memory_id": memory_id,
                    "importance_score": importance_score,
                    "reason": "Importance threshold met"
                }
            else:
                return {
                    "stored": False,
                    "importance_score": importance_score,
                    "reason": f"Importance score {importance_score:.2f} below threshold {self.min_importance_score}"
                }
                
        except Exception as e:
            app_logger.error(f"Long-term memory processing failed: {e}")
            return {
                "stored": False,
                "importance_score": 0.0,
                "error": str(e)
            }
    
    async def search_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_importance: float = 0.0,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """搜索相关的长期记忆"""
        if not self.enabled:
            return {
                "memories": [],
                "metadata": {
                    "enabled": False,
                    "reason": "Long-term memory disabled"
                }
            }
        
        try:
            # 1. 语义搜索
            semantic_results = await self.semantic_search.search_semantic_memories(
                query=query,
                user_id=user_id,
                limit=limit,
                min_importance=min_importance,
                time_range=time_range
            )
            
            # 2. 按意图搜索
            intent_results = await self.semantic_search.search_by_intent(
                intent=query,
                user_id=user_id,
                limit=limit // 2
            )
            
            # 3. 合并结果
            all_memories = semantic_results + intent_results
            
            return {
                "memories": all_memories,
                "metadata": {
                    "enabled": True,
                    "semantic_count": len(semantic_results),
                    "intent_count": len(intent_results),
                    "total_count": len(all_memories),
                    "query": query,
                    "limit": limit
                }
            }
            
        except Exception as e:
            app_logger.error(f"Failed to search relevant memories: {e}")
            return {
                "memories": [],
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        if not self.enabled:
            return {
                "profile": {},
                "metadata": {
                    "enabled": False,
                    "reason": "Long-term memory disabled"
                }
            }
        
        try:
            profile = await self.profile_service.get_user_profile(user_id)
            
            return {
                "profile": profile,
                "metadata": {
                    "enabled": True,
                    "profile_fields": len(profile),
                    "last_updated": profile.get("last_updated", "unknown")
                }
            }
            
        except Exception as e:
            app_logger.error(f"Failed to get user profile: {e}")
            return {
                "profile": {},
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    async def get_memory_timeline(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取记忆时间线"""
        if not self.enabled:
            return {
                "timeline": [],
                "metadata": {
                    "enabled": False,
                    "reason": "Long-term memory disabled"
                }
            }
        
        try:
            timeline = await self.semantic_search.get_memory_timeline(
                user_id=user_id,
                days=days,
                limit=limit
            )
            
            return {
                "timeline": timeline,
                "metadata": {
                    "enabled": True,
                    "days": days,
                    "limit": limit,
                    "count": len(timeline)
                }
            }
            
        except Exception as e:
            app_logger.error(f"Failed to get memory timeline: {e}")
            return {
                "timeline": [],
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    async def _extract_user_profile(
        self,
        user_id: str,
        message: str,
        response: str
    ) -> None:
        """提取用户画像信息"""
        try:
            await self.profile_service.extract_user_preferences(
                user_id=user_id,
                message=message,
                conversation_context={
                    "user_id": user_id,
                    "turn_count": 1
                }
            )
        except Exception as e:
            app_logger.error(f"Failed to extract user profile: {e}")
    
    async def _store_semantic_memory(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        importance_score: float,
        intent: str,
        sources: List[str] = None
    ) -> str:
        """存储语义记忆"""
        try:
            # 生成嵌入向量
            content = f"问题：{message}\n回答：{response}"
            embedding = await self.embedding_service.embed_text(content)
            
            if not embedding:
                raise Exception("Failed to generate embedding")
            
            # 存储到Qdrant
            memory_id = await self.qdrant_manager.add_semantic_memory(
                content=content,
                embedding=embedding,
                user_id=user_id,
                conversation_id=conversation_id,
                importance_score=importance_score,
                metadata={
                    "intent": intent,
                    "sources": sources or [],
                    "created_at": datetime.now().isoformat(),
                    "message_length": len(message),
                    "response_length": len(response)
                }
            )
            
            return memory_id
            
        except Exception as e:
            app_logger.error(f"Failed to store semantic memory: {e}")
            return ""
    
    async def cleanup_old_memories(
        self,
        user_id: str,
        days_threshold: int = None
    ) -> Dict[str, Any]:
        """清理旧的记忆"""
        if not self.enabled:
            return {
                "cleaned": 0,
                "metadata": {
                    "enabled": False,
                    "reason": "Long-term memory disabled"
                }
            }
        
        try:
            days_threshold = days_threshold or self.memory_decay_days
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            # 这里应该实现具体的清理逻辑
            # 由于Qdrant没有直接的按时间删除方法，这里简化处理
            
            return {
                "cleaned": 0,
                "metadata": {
                    "enabled": True,
                    "days_threshold": days_threshold,
                    "cutoff_date": cutoff_date.isoformat(),
                    "note": "Cleanup logic needs implementation"
                }
            }
            
        except Exception as e:
            app_logger.error(f"Failed to cleanup old memories: {e}")
            return {
                "cleaned": 0,
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Long-term memory is disabled",
                "components": {
                    "qdrant_manager": "disabled",
                    "profile_service": "disabled",
                    "semantic_search": "disabled",
                    "importance_calculator": "disabled"
                }
            }
        
        try:
            # 检查各个组件
            qdrant_health = await self.qdrant_manager.health_check()
            
            return {
                "status": "ok",
                "message": "Long-term memory is healthy",
                "components": {
                    "qdrant_manager": qdrant_health["status"],
                    "profile_service": "ok",
                    "semantic_search": "ok",
                    "importance_calculator": "ok"
                },
                "config": {
                    "min_importance_score": self.min_importance_score,
                    "max_memories_per_user": self.max_memories_per_user,
                    "memory_decay_days": self.memory_decay_days,
                    "enabled": self.enabled
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Long-term memory health check failed: {e}",
                "components": {
                    "qdrant_manager": "error",
                    "profile_service": "unknown",
                    "semantic_search": "unknown",
                    "importance_calculator": "unknown"
                }
            }
    
    def set_enabled(self, enabled: bool) -> None:
        """动态启用/禁用长期记忆"""
        self.enabled = enabled
        app_logger.info(f"Long-term memory {'enabled' if enabled else 'disabled'}")
    
    def update_config(
        self,
        min_importance_score: float = None,
        max_memories_per_user: int = None,
        memory_decay_days: int = None
    ) -> None:
        """更新配置"""
        if min_importance_score is not None:
            self.min_importance_score = min_importance_score
        if max_memories_per_user is not None:
            self.max_memories_per_user = max_memories_per_user
        if memory_decay_days is not None:
            self.memory_decay_days = memory_decay_days
        
        app_logger.info(f"Long-term memory config updated: min_importance={self.min_importance_score}")


# 全局实例 - 默认启用
long_term_memory = LongTermMemory(enabled=True)

