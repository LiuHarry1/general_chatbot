"""
统一记忆接口模块
提供对短期记忆和长期记忆的统一访问接口
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from utils.logger import app_logger
from memory.short_term_memory import short_term_memory
from memory.long_term_memory import long_term_memory

logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """统一记忆管理器"""
    
    def __init__(
        self,
        short_term_enabled: bool = True,
        long_term_enabled: bool = True
    ):
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        
        # 设置启用状态
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
    
    async def get_conversation_context(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """获取完整的对话上下文"""
        app_logger.info(f"🧠 [UNIFIED] Getting conversation context for {user_id}:{conversation_id}")
        app_logger.info(f"💬 [UNIFIED] Current message: {current_message[:100]}...")
        
        context = {
            "short_term_context": "",
            "long_term_context": "",
            "user_profile": {},
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
                app_logger.info(f"🔍 [UNIFIED] Getting short-term context")
                tasks.append(
                    self.short_term_memory.get_recent_context(
                        user_id, conversation_id, limit
                    )
                )
            else:
                app_logger.info(f"🔍 [UNIFIED] Short-term memory disabled")
                tasks.append(asyncio.create_task(self._empty_short_term_context()))
            
            # 获取长期记忆上下文
            if self.long_term_memory.enabled:
                app_logger.info(f"🔍 [UNIFIED] Getting long-term context")
                tasks.append(
                    self.long_term_memory.search_relevant_memories(
                        user_id, current_message, limit
                    )
                )
            else:
                app_logger.info(f"🔍 [UNIFIED] Long-term memory disabled")
                tasks.append(asyncio.create_task(self._empty_long_term_context()))
            
            # 获取用户画像
            if self.long_term_memory.enabled:
                app_logger.info(f"🔍 [UNIFIED] Getting user profile")
                tasks.append(
                    self.long_term_memory.get_user_profile(user_id)
                )
            else:
                app_logger.info(f"🔍 [UNIFIED] User profile disabled")
                tasks.append(asyncio.create_task(self._empty_user_profile()))
            
            # 等待所有任务完成
            short_term_result, long_term_result, profile_result = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            
            # 处理短期记忆结果
            if isinstance(short_term_result, Exception):
                app_logger.error(f"❌ [UNIFIED] Short-term memory error: {short_term_result}")
                context["short_term_context"] = ""
                context["metadata"]["short_term_error"] = str(short_term_result)
            else:
                context["short_term_context"] = short_term_result.get("context", "")
                context["metadata"]["short_term_metadata"] = short_term_result.get("metadata", {})
                app_logger.info(f"✅ [UNIFIED] Short-term context length: {len(context['short_term_context'])} characters")
                if context["short_term_context"]:
                    app_logger.info(f"📄 [UNIFIED] Short-term content: {context['short_term_context'][:200]}...")
            
            # 处理长期记忆结果
            if isinstance(long_term_result, Exception):
                app_logger.error(f"❌ [UNIFIED] Long-term memory error: {long_term_result}")
                context["long_term_context"] = ""
                context["metadata"]["long_term_error"] = str(long_term_result)
            else:
                memories = long_term_result.get("memories", [])
                context["long_term_context"] = self._format_long_term_memories(memories)
                context["metadata"]["long_term_metadata"] = long_term_result.get("metadata", {})
                app_logger.info(f"✅ [UNIFIED] Long-term memories found: {len(memories)}")
                app_logger.info(f"📄 [UNIFIED] Long-term context length: {len(context['long_term_context'])} characters")
                if context["long_term_context"]:
                    app_logger.info(f"📄 [UNIFIED] Long-term content: {context['long_term_context'][:200]}...")
                
                # 打印每个记忆的详细信息
                for i, memory in enumerate(memories):
                    app_logger.info(f"🧠 [LONG-TERM] Memory {i+1}: {memory.get('content', '')[:100]}... (importance: {memory.get('importance_score', 0):.2f})")
            
            # 处理用户画像结果
            if isinstance(profile_result, Exception):
                app_logger.error(f"❌ [UNIFIED] User profile error: {profile_result}")
                context["user_profile"] = {}
                context["metadata"]["profile_error"] = str(profile_result)
            else:
                context["user_profile"] = profile_result.get("profile", {})
                context["metadata"]["profile_metadata"] = profile_result.get("metadata", {})
                app_logger.info(f"✅ [UNIFIED] User profile retrieved for {user_id}")
                
                # 打印用户画像详细信息
                profile = context["user_profile"]
                if profile:
                    app_logger.info(f"👤 [USER-PROFILE] Identity: {profile.get('identity', {})}")
                    app_logger.info(f"🎯 [USER-PROFILE] Preferences: {profile.get('preferences', [])}")
                    app_logger.info(f"💡 [USER-PROFILE] Interests: {profile.get('interests', [])}")
                    app_logger.info(f"📊 [USER-PROFILE] Behavior patterns: {profile.get('behavior_patterns', [])}")
                else:
                    app_logger.info(f"👤 [USER-PROFILE] No profile data found for {user_id}")
            
            # 构建完整上下文
            context["full_context"] = self._build_full_context(context)
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
    
    def _build_full_context(self, context: Dict[str, Any]) -> str:
        """构建完整的上下文"""
        parts = []
        
        # 添加用户画像信息
        user_profile = context.get("user_profile", {})
        if user_profile:
            parts.append("以下是关于用户的一些已知信息，请在对话中自然地利用这些信息，让用户感受到你认识他们：")
            parts.append(self._format_user_profile(user_profile))
        
        # 添加长期记忆上下文
        long_term_context = context.get("long_term_context", "")
        if long_term_context:
            parts.append("\n相关历史记忆：")
            parts.append(long_term_context)
        
        # 添加短期记忆上下文
        short_term_context = context.get("short_term_context", "")
        if short_term_context:
            parts.append("\n最近对话：")
            parts.append(short_term_context)
        
        full_context = "\n".join(parts)
        
        # 打印最终prompt的详细内容
        app_logger.info("=" * 80)
        app_logger.info("🤖 [FINAL-PROMPT] 最终喂给大语言模型的完整Prompt:")
        app_logger.info("=" * 80)
        
        if user_profile:
            app_logger.info("👤 [USER-PROFILE] 用户画像数据:")
            app_logger.info(f"📄 [USER-PROFILE] {self._format_user_profile(user_profile)}")
        else:
            app_logger.info("👤 [USER-PROFILE] 无用户画像数据")
        
        if long_term_context:
            app_logger.info("🧠 [LONG-TERM] 长期记忆数据:")
            app_logger.info(f"📄 [LONG-TERM] {long_term_context}")
        else:
            app_logger.info("🧠 [LONG-TERM] 无长期记忆数据")
        
        if short_term_context:
            app_logger.info("💬 [SHORT-TERM] 短期记忆数据:")
            app_logger.info(f"📄 [SHORT-TERM] {short_term_context}")
        else:
            app_logger.info("💬 [SHORT-TERM] 无短期记忆数据")
        
        app_logger.info("🤖 [FINAL-PROMPT] 完整Prompt内容:")
        app_logger.info(f"📄 [FINAL-PROMPT] {full_context}")
        app_logger.info("=" * 80)
        
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


# 全局实例 - 默认都启用
unified_memory_manager = UnifiedMemoryManager(
    short_term_enabled=True,
    long_term_enabled=True
)
