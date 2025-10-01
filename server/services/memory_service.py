"""
智能记忆管理服务
实现完整的记忆架构：
1. 短期记忆：从数据库读取 + 智能压缩（>1k tokens自动summary）
2. 长期记忆：
   - 用户画像/偏好：自动提取并存储（Redis缓存）
   - 语义记忆：向量数据库 + 语义搜索相似对话
"""
import asyncio
import tiktoken
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from utils.logger import app_logger
from memory import default_memory_manager as memory_manager
from services.ai_service import ai_service


class MemoryService:
    """
    智能记忆管理服务
    
    三层记忆架构：
    1. 短期记忆：数据库最近对话 + 智能压缩（>1k tokens）
    2. 用户画像：自动提取偏好/兴趣/身份信息（Redis缓存）
    3. 语义记忆：向量数据库存储重要对话 + 语义搜索
    """
    
    def __init__(self):
        self.memory_manager = memory_manager
        self.ai_service = ai_service
        self.encoder = tiktoken.encoding_for_model("gpt-4")
        
        # 短期记忆配置
        self.max_short_term_tokens = 1000  # 超过1k tokens触发压缩
        self.recent_turns = 3  # 保留最近3轮对话原文
        self.summary_cache = {}  # 摘要缓存
        
        # 长期记忆配置
        self.min_importance_score = 0.6  # 语义记忆重要性阈值
        
        # 用户画像配置
        self.preference_keywords = [
            "我喜欢", "我不喜欢", "我讨厌", "我爱", "我讨厌",
            "我是", "我在", "我的", "我想", "我希望", "我需要"
        ]
        
        app_logger.info(
            f"记忆服务初始化 - "
            f"短期记忆阈值: {self.max_short_term_tokens} tokens, "
            f"保留轮数: {self.recent_turns}, "
            f"长期记忆重要性阈值: {self.min_importance_score}"
        )
    
    def _count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            app_logger.error(f"Token计数失败: {e}")
            # 降级：使用字符数估算（中文约1.5字符=1token）
            return len(text) // 2
    
    def _format_message(self, msg: Dict[str, Any]) -> str:
        """格式化单条消息"""
        role_name = "用户" if msg['role'] == 'user' else "助手"
        return f"{role_name}: {msg['content']}"
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """格式化消息列表"""
        return "\n".join(self._format_message(msg) for msg in messages)
    
    async def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        使用LLM生成对话历史摘要
        保留关键信息：话题、结论、重要事实
        """
        try:
            if not messages:
                return ""
            
            # 构建对话历史文本
            history_text = self._format_messages(messages)
            
            # 调用LLM生成摘要
            summary_prompt = f"""
请为以下对话历史生成一个简洁的摘要。

要求：
1. 保留关键话题和重要信息
2. 记录用户的问题和需求
3. 记录重要的结论和建议
4. 控制在200字以内
5. 使用第三人称描述

对话历史：
{history_text}

请生成摘要：
"""
            
            summary = await self.ai_service.generate_response(
                user_message=summary_prompt,
                intent="normal",
                file_content=None,
                web_content=None,
                search_results=None,
                user_identity={},
                contextual_prompt="",
                short_term_context=""
            )
            
            app_logger.info(f"成功生成摘要，原始消息数: {len(messages)}, 摘要长度: {len(summary)}")
            return summary.strip()
            
        except Exception as e:
            app_logger.error(f"生成摘要失败: {e}")
            # 降级：返回简单的文本摘要
            return f"[包含 {len(messages)} 条历史消息]"
    
    async def get_short_term_context(
        self, 
        conversation_id: str,
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        获取短期记忆上下文（智能压缩）
        
        Args:
            conversation_id: 对话ID
            messages: 可选的消息列表，如果不提供则从数据库读取
            
        Returns:
            (context_text, metadata): 上下文文本和元数据
        """
        try:
            # 如果没有提供消息，从数据库读取
            if messages is None:
                from database import message_repo
                messages = message_repo.get_messages(conversation_id)
            
            if not messages:
                return "", {"total_messages": 0, "compressed": False}
            
            # 计算总token数
            total_text = "\n".join(msg['content'] for msg in messages)
            total_tokens = self._count_tokens(total_text)
            
            app_logger.debug(f"对话 {conversation_id} 的token数: {total_tokens}, 消息数: {len(messages)}")
            
            # 如果token数在限制内，直接返回所有消息
            if total_tokens <= self.max_short_term_tokens:
                context = self._format_messages(messages)
                return context, {
                    "total_messages": len(messages),
                    "total_tokens": total_tokens,
                    "compressed": False,
                    "summary": None
                }
            
            # 需要压缩：保留最近N轮对话，旧的生成摘要
            recent_count = self.recent_turns * 2  # N轮 = N个用户消息 + N个助手回复
            recent_messages = messages[-recent_count:] if len(messages) > recent_count else messages
            old_messages = messages[:-recent_count] if len(messages) > recent_count else []
            
            # 检查缓存
            cache_key = f"{conversation_id}:{len(old_messages)}"
            summary = self.summary_cache.get(cache_key)
            
            if not summary and old_messages:
                # 生成新的摘要
                app_logger.info(f"为对话 {conversation_id} 生成摘要，旧消息数: {len(old_messages)}")
                summary = await self._generate_summary(old_messages)
                # 缓存摘要（简单的内存缓存，生产环境应该用Redis）
                self.summary_cache[cache_key] = summary
                
                # 限制缓存大小
                if len(self.summary_cache) > 100:
                    # 删除最老的缓存
                    oldest_key = list(self.summary_cache.keys())[0]
                    del self.summary_cache[oldest_key]
            
            # 构建压缩后的上下文
            if summary:
                context = f"""【对话历史摘要】（{len(old_messages)}条消息）
{summary}

【最近对话】
{self._format_messages(recent_messages)}"""
            else:
                context = self._format_messages(recent_messages)
            
            # 计算压缩后的token数
            compressed_tokens = self._count_tokens(context)
            compression_ratio = compressed_tokens / total_tokens if total_tokens > 0 else 1.0
            
            app_logger.info(
                f"对话 {conversation_id} 已压缩 - "
                f"原始: {len(messages)}条/{total_tokens}tokens, "
                f"压缩后: {compressed_tokens}tokens, "
                f"压缩率: {compression_ratio:.2%}"
            )
            
            return context, {
                "total_messages": len(messages),
                "total_tokens": total_tokens,
                "compressed": True,
                "compressed_tokens": compressed_tokens,
                "compression_ratio": compression_ratio,
                "recent_messages": len(recent_messages),
                "summarized_messages": len(old_messages),
                "summary": summary
            }
            
        except Exception as e:
            app_logger.error(f"获取短期记忆上下文失败: {e}")
            # 降级：返回空上下文
            return "", {"error": str(e), "compressed": False}
    
    async def get_long_term_context(
        self,
        user_id: str,
        current_message: str,
        limit: int = 3
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        获取长期记忆上下文
        
        包含两部分：
        1. 用户画像/偏好
        2. 语义相似的历史对话
        
        Args:
            user_id: 用户ID
            current_message: 当前消息
            limit: 返回最相似的N条对话
            
        Returns:
            (context_text, user_profile): 上下文文本和用户画像
        """
        context_parts = []
        user_profile = None
        
        try:
            # 1. 获取用户画像
            try:
                user_profile = await self.memory_manager.get_user_identity(user_id)
                if user_profile and user_profile.get('identity'):
                    identity = user_profile['identity']
                    profile_parts = ["【用户画像】"]
                    
                    if identity.get('name'):
                        profile_parts.append(f"姓名：{identity['name']}")
                    if identity.get('age'):
                        profile_parts.append(f"年龄：{identity['age']}")
                    if identity.get('location'):
                        profile_parts.append(f"居住地：{identity['location']}")
                    if identity.get('job'):
                        profile_parts.append(f"职业：{identity['job']}")
                    
                    if user_profile.get('interests'):
                        profile_parts.append(f"兴趣：{', '.join(user_profile['interests'])}")
                    if user_profile.get('preferences'):
                        profile_parts.append(f"偏好：{', '.join(user_profile['preferences'])}")
                    
                    if len(profile_parts) > 1:  # 有实际内容
                        context_parts.append("\n".join(profile_parts))
                        app_logger.info(f"获取到用户画像: {user_id}")
            except Exception as e:
                app_logger.warning(f"获取用户画像失败: {e}")
            
            # 2. 语义搜索相似的历史对话
            try:
                similar_memories = await self.memory_manager.search_relevant_context(
                    query=current_message,
                    user_id=user_id,
                    limit=limit
                )
                
                if similar_memories:
                    memory_parts = ["【相关历史对话】"]
                    for i, memory in enumerate(similar_memories, 1):
                        memory_text = memory.get('content', '') if isinstance(memory, dict) else str(memory)
                        if memory_text:
                            # 截取前200字符避免太长
                            preview = memory_text[:200] + "..." if len(memory_text) > 200 else memory_text
                            memory_parts.append(f"{i}. {preview}")
                    
                    context_parts.append("\n".join(memory_parts))
                    app_logger.info(f"找到 {len(similar_memories)} 条相似历史对话")
            except Exception as e:
                app_logger.warning(f"语义搜索失败: {e}")
            
            # 3. 合并上下文
            if context_parts:
                full_context = "\n\n".join(context_parts)
                return full_context, user_profile
            
            return "", user_profile
            
        except Exception as e:
            app_logger.error(f"获取长期记忆上下文失败: {e}")
            return "", None
    
    def _calculate_importance(
        self,
        message: str,
        response: str,
        intent: str
    ) -> float:
        """
        计算对话的重要性评分（0-1）
        
        评分因素：
        1. 对话长度（长对话更重要）
        2. Intent类型（search/file/web > normal）
        3. 是否包含决策词汇
        4. 是否包含个人信息
        """
        score = 0.0
        
        # 1. 长度因素（最多0.3分）
        total_length = len(message) + len(response)
        if total_length > 500:
            score += 0.3
        elif total_length > 200:
            score += 0.2
        elif total_length > 100:
            score += 0.1
        
        # 2. Intent因素（最多0.4分）
        intent_scores = {
            'search': 0.4,
            'web': 0.4,
            'file': 0.4,
            'code': 0.3,
            'normal': 0.1
        }
        score += intent_scores.get(intent, 0.1)
        
        # 3. 决策词汇（最多0.2分）
        decision_keywords = [
            "决定", "选择", "打算", "计划", "需要",
            "重要", "关键", "必须", "一定"
        ]
        if any(keyword in message or keyword in response for keyword in decision_keywords):
            score += 0.2
        
        # 4. 个人信息（最多0.1分）
        personal_keywords = [
            "我的", "我在", "我是", "我会", "我想"
        ]
        if any(keyword in message for keyword in personal_keywords):
            score += 0.1
        
        return min(score, 1.0)  # 确保不超过1.0
    
    async def save_to_long_term(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str]
    ) -> bool:
        """
        保存对话到长期记忆（向量数据库）
        
        策略：
        1. 计算重要性评分
        2. 评分 >= 阈值的对话保存到向量数据库
        3. 后续可以通过语义搜索检索相似对话
        """
        try:
            # 计算重要性
            importance = self._calculate_importance(message, response, intent)
            
            app_logger.debug(
                f"对话重要性评分: {importance:.2f} - "
                f"user_id={user_id}, intent={intent}, "
                f"message_length={len(message)}"
            )
            
            # 保存重要对话到向量数据库
            if importance >= self.min_importance_score:
                # 构建记忆文本（包含问答完整内容，便于语义搜索）
                memory_text = f"问题：{message}\n回答：{response[:300]}..."
                
                success = await self.memory_manager.add_memory(
                    user_id=user_id,
                    memory_text=memory_text,
                    metadata={
                        "intent": intent,
                        "sources": sources,
                        "conversation_id": conversation_id,
                        "importance": importance,
                        "timestamp": datetime.now().isoformat(),
                        "message": message,
                        "response_preview": response[:200]
                    }
                )
                
                if success:
                    app_logger.info(
                        f"对话已保存到长期记忆（向量数据库） - "
                        f"user_id={user_id}, importance={importance:.2f}, intent={intent}"
                    )
                
                return success
            else:
                app_logger.debug(f"对话重要性不足，跳过长期存储: {importance:.2f}")
                return False
                
        except Exception as e:
            app_logger.error(f"保存长期记忆失败: {e}")
            return False
    
    async def extract_user_preferences(
        self,
        user_id: str,
        message: str
    ) -> bool:
        """
        从消息中提取用户偏好/画像
        
        检测偏好信号词，自动提取并更新用户画像
        
        Args:
            user_id: 用户ID
            message: 用户消息
            
        Returns:
            是否成功提取到偏好信息
        """
        try:
            # 检测是否包含偏好信号
            has_signal = any(keyword in message for keyword in self.preference_keywords)
            
            if not has_signal:
                return False
            
            # 使用LLM提取用户偏好
            identity_info = await self.memory_manager.extract_identity_from_message(
                message=message,
                user_id=user_id
            )
            
            if identity_info:
                app_logger.info(f"自动提取到用户偏好: {user_id} - {identity_info}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"提取用户偏好失败: {e}")
            return False
    
    async def update_memories_async(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        intent: str,
        sources: List[str]
    ):
        """
        异步更新长期记忆（后台任务）
        不阻塞主对话流程
        
        完整策略：
        1. 提取用户偏好（自动检测偏好信号词）
        2. 保存重要对话到向量数据库（基于重要性评分）
        """
        try:
            # 1. 自动提取用户偏好/画像
            await self.extract_user_preferences(user_id, message)
            
            # 2. 保存到语义记忆（向量数据库）
            await self.save_to_long_term(
                user_id, conversation_id, message, response, intent, sources
            )
            
        except Exception as e:
            app_logger.error(f"异步更新记忆失败（不影响主流程）: {e}")
    
    def clear_summary_cache(self, conversation_id: Optional[str] = None):
        """清空摘要缓存"""
        if conversation_id:
            # 清空特定对话的缓存
            keys_to_remove = [k for k in self.summary_cache.keys() if k.startswith(f"{conversation_id}:")]
            for key in keys_to_remove:
                del self.summary_cache[key]
            app_logger.info(f"已清空对话 {conversation_id} 的摘要缓存")
        else:
            # 清空所有缓存
            self.summary_cache.clear()
            app_logger.info("已清空所有摘要缓存")


# 全局实例
memory_service = MemoryService()

