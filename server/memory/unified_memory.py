"""
统一记忆接口模块
提供对短期记忆和长期记忆的统一访问接口
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from utils.logger import app_logger, log_execution_time
from memory.short_term_memory import short_term_memory
from memory.long_term_memory import long_term_memory
from config.settings import settings

logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """统一记忆管理器"""
    
    def __init__(
        self,
        short_term_enabled: bool = None,
        long_term_enabled: bool = None
    ):
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        
        # 设置启用状态 - 从配置文件读取，如果未提供则使用配置文件的值
        short_term_enabled = short_term_enabled if short_term_enabled is not None else settings.short_term_memory_enabled
        long_term_enabled = long_term_enabled if long_term_enabled is not None else settings.long_term_memory_enabled
        
        self.short_term_memory.enabled = short_term_enabled
        self.long_term_memory.set_enabled(long_term_enabled)
        
        app_logger.info(
            f"UnifiedMemoryManager initialized - "
            f"Short-term: {short_term_enabled}, Long-term: {long_term_enabled}"
        )
    
    async def process_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """处理对话，同时更新短期和长期记忆"""
        app_logger.info(f"🔄 [UNIFIED] Processing conversation for {user_id}:{conversation_id}")
        app_logger.info(f"💬 [UNIFIED] Message: {message[:100]}...")
        app_logger.info(f"🤖 [UNIFIED] Response: {response[:100]}...")
        app_logger.info(f"🎯 [UNIFIED] Intent: {intent}")
        app_logger.info(f"📚 [UNIFIED] Sources: {sources}")
        
        results = {
            "success": True,
            "short_term": {},
            "long_term": {},
            "metadata": {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "intent": intent,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            # 并行处理短期和长期记忆
            tasks = []
            
            # 短期记忆处理
            if self.short_term_memory.enabled:
                tasks.append(
                    self._process_short_term(
                        user_id, conversation_id, message, response
                    )
                )
            
            # 长期记忆处理
            if self.long_term_memory.enabled:
                tasks.append(
                    self._process_long_term(
                        user_id, conversation_id, message, response, intent, sources
                    )
                )
            
            # 等待所有任务完成
            if tasks:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 根据启用的模块分配结果
                result_index = 0
                if self.short_term_memory.enabled:
                    if isinstance(task_results[result_index], Exception):
                        results["short_term"] = {"error": str(task_results[result_index])}
                    else:
                        results["short_term"] = task_results[result_index]
                    result_index += 1
                else:
                    results["short_term"] = {"enabled": False}
                
                if self.long_term_memory.enabled:
                    if isinstance(task_results[result_index], Exception):
                        results["long_term"] = {"error": str(task_results[result_index])}
                    else:
                        results["long_term"] = task_results[result_index]
                else:
                    results["long_term"] = {"enabled": False}
            else:
                results["short_term"] = {"enabled": False}
                results["long_term"] = {"enabled": False}
            
            return results
            
        except Exception as e:
            app_logger.error(f"Conversation processing failed: {e}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    @log_execution_time(threshold_ms=50)
    async def get_conversation_context(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """获取完整的对话上下文"""
        context = {
            "full_context": "",  # 只返回 full_context，包含所有记忆
            "metadata": {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            tasks = []
            
            # 获取短期记忆上下文
            if self.short_term_memory.enabled:
                tasks.append(
                    self.short_term_memory.get_recent_context(
                        user_id, conversation_id, limit
                    )
                )
            else:
                tasks.append(asyncio.create_task(self._empty_short_term_context()))
            
            # 获取长期记忆上下文
            if self.long_term_memory.enabled:
                tasks.append(
                    self.long_term_memory.search_relevant_memories(
                        user_id, current_message, limit
                    )
                )
            else:
                tasks.append(asyncio.create_task(self._empty_long_term_context()))
            
            # 获取用户画像
            if self.long_term_memory.enabled:
                tasks.append(
                    self.long_term_memory.get_user_profile(user_id)
                )
            else:
                tasks.append(asyncio.create_task(self._empty_user_profile()))
            
            # 等待所有任务完成
            short_term_result, long_term_result, profile_result = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            
            # 处理短期记忆结果
            short_term_context = ""
            if isinstance(short_term_result, Exception):
                app_logger.error(f"❌ Short-term memory error: {short_term_result}")
                context["metadata"]["short_term_error"] = str(short_term_result)
            else:
                short_term_context = short_term_result.get("context", "")
                context["metadata"]["short_term_metadata"] = short_term_result.get("metadata", {})
            
            # 处理长期记忆结果
            long_term_memories = []
            if isinstance(long_term_result, Exception):
                app_logger.error(f"❌ Long-term memory error: {long_term_result}")
                context["metadata"]["long_term_error"] = str(long_term_result)
            else:
                long_term_memories = long_term_result.get("memories", [])
                context["metadata"]["long_term_metadata"] = long_term_result.get("metadata", {})
            
            # 处理用户画像结果
            user_profile = {}
            if isinstance(profile_result, Exception):
                app_logger.error(f"❌ User profile error: {profile_result}")
                context["metadata"]["profile_error"] = str(profile_result)
            else:
                user_profile = profile_result.get("profile", {})
                context["metadata"]["profile_metadata"] = profile_result.get("metadata", {})
            
            # 构建完整上下文 - 包含所有记忆信息
            context["full_context"] = self._build_full_context(
                user_profile=user_profile,
                long_term_memories=long_term_memories,
                short_term_context=short_term_context
            )
            app_logger.info(f"📄 [UNIFIED] Full context length: {len(context['full_context'])} characters")
            app_logger.info(f"📄 [UNIFIED] Full context: {context['full_context'][:300]}...")
            
            return context
            
        except Exception as e:
            app_logger.error(f"Failed to get conversation context: {e}")
            context["error"] = str(e)
            return context
    
    async def _process_short_term(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str
    ) -> Dict[str, Any]:
        """处理短期记忆"""
        # 使用智能存储到短期记忆
        stored = await self.short_term_memory.smart_store_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            response=response,
            metadata={}
        )
        
        return {
            "stored": stored,
            "enabled": True,
            "type": "short_term"
        }
    
    async def _process_long_term(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str]
    ) -> Dict[str, Any]:
        """处理长期记忆"""
        result = await self.long_term_memory.process_conversation_for_storage(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            response=response,
            intent=intent,
            sources=sources
        )
        
        return {
            **result,
            "enabled": True,
            "type": "long_term"
        }
    
    async def _empty_short_term_context(self) -> Dict[str, Any]:
        """空的短期记忆上下文"""
        return {
            "context": "",
            "metadata": {
                "enabled": False,
                "reason": "Short-term memory disabled"
            }
        }
    
    async def _empty_long_term_context(self) -> Dict[str, Any]:
        """空的长期记忆上下文"""
        return {
            "memories": [],
            "metadata": {
                "enabled": False,
                "reason": "Long-term memory disabled"
            }
        }
    
    async def _empty_user_profile(self) -> Dict[str, Any]:
        """空的用户画像"""
        return {
            "profile": {},
            "metadata": {
                "enabled": False,
                "reason": "Long-term memory disabled"
            }
        }
    
    def _format_long_term_memories(self, memories: List[Dict[str, Any]]) -> str:
        """格式化长期记忆"""
        if not memories:
            return ""
        
        formatted = []
        for memory in memories[:3]:  # 最多3条记忆
            content = memory.get("content", "")
            importance = memory.get("importance_score", 0)
            created_at = memory.get("created_at", "")
            
            formatted.append(f"[重要性: {importance:.2f}] {content[:100]}...")
        
        return "\n".join(formatted)
    
    def _build_full_context(
        self, 
        user_profile: Dict[str, Any],
        long_term_memories: List[Dict[str, Any]],
        short_term_context: str
    ) -> str:
        """构建完整的上下文，包含所有记忆信息"""
        parts = []
        
        # 添加用户画像信息
        if user_profile:
            parts.append("以下是关于用户的一些已知信息，请在对话中自然地利用这些信息，让用户感受到你认识他们：")
            parts.append(self._format_user_profile(user_profile))
        
        # 添加长期记忆上下文
        long_term_context = self._format_long_term_memories(long_term_memories)
        if long_term_context:
            parts.append("\n相关历史记忆：")
            parts.append(long_term_context)
        
        # 添加短期记忆上下文
        if short_term_context:
            parts.append("\n最近对话：")
            parts.append(short_term_context)
        
        full_context = "\n".join(parts)
        return full_context
    
    def _format_user_profile(self, profile: Dict[str, Any]) -> str:
        """格式化用户画像"""
        if not profile:
            return ""
        
        formatted = []
        
        # 身份信息
        identity = profile.get("identity", {})
        if identity:
            formatted.append("【用户身份】")
            for key, value in identity.items():
                if value:
                    formatted.append(f"{key}：{value}")
        
        # 偏好信息
        preferences = profile.get("preferences", [])
        if preferences:
            formatted.append("【用户偏好】" + ", ".join(preferences))
        
        # 兴趣信息
        interests = profile.get("interests", [])
        if interests:
            formatted.append("【用户兴趣】" + ", ".join(interests))
        
        return "\n".join(formatted)
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 并行检查短期和长期记忆
            short_term_health = await self.short_term_memory.health_check()
            long_term_health = await self.long_term_memory.health_check()
            
            overall_status = "ok"
            if short_term_health["status"] == "error" or long_term_health["status"] == "error":
                overall_status = "error"
            elif short_term_health["status"] == "disabled" and long_term_health["status"] == "disabled":
                overall_status = "disabled"
            
            return {
                "status": overall_status,
                "message": f"Unified memory system status: {overall_status}",
                "short_term": short_term_health,
                "long_term": long_term_health,
                "config": {
                    "short_term_enabled": self.short_term_memory.enabled,
                    "long_term_enabled": self.long_term_memory.enabled
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {e}",
                "short_term": {"status": "unknown"},
                "long_term": {"status": "unknown"}
            }
    
    def configure(
        self,
        short_term_enabled: bool = None,
        long_term_enabled: bool = None,
        **kwargs
    ) -> None:
        """配置记忆系统"""
        if short_term_enabled is not None:
            self.short_term_memory.enabled = short_term_enabled
            app_logger.info(f"Short-term memory {'enabled' if short_term_enabled else 'disabled'}")
        
        if long_term_enabled is not None:
            self.long_term_memory.set_enabled(long_term_enabled)
            app_logger.info(f"Long-term memory {'enabled' if long_term_enabled else 'disabled'}")
        
        # 更新长期记忆配置
        if kwargs:
            self.long_term_memory.update_config(**kwargs)


# 全局实例 - 从配置文件读取启用状态
unified_memory_manager = UnifiedMemoryManager()
