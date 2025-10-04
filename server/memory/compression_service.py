"""
智能压缩服务
实现对话历史的智能摘要和压缩
"""
import asyncio
import tiktoken
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import logging
import json

from utils.logger import app_logger
from services.ai_service import ai_service
from memory.importance_calculator import importance_calculator

logger = logging.getLogger(__name__)


class CompressionService:
    """智能压缩服务"""
    
    def __init__(self):
        self.encoder = tiktoken.encoding_for_model("gpt-4")
        
        # 压缩配置
        self.max_short_term_tokens = 1000
        self.recent_turns = 3  # 保留最近3轮对话
        self.min_compression_ratio = 0.3  # 最小压缩比
        self.max_summary_length = 500  # 最大摘要长度
        
        # 摘要缓存
        self.summary_cache = {}
        self.cache_max_size = 100
        
        app_logger.info("CompressionService initialized")
    
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
    
    async def _generate_ai_summary(
        self,
        messages: List[Dict[str, Any]],
        conversation_context: Dict[str, Any] = None
    ) -> str:
        """使用AI生成对话摘要"""
        try:
            if not messages:
                return ""
            
            # 构建对话历史文本
            history_text = self._format_messages(messages)
            
            # 构建摘要提示词
            context_info = ""
            if conversation_context:
                user_id = conversation_context.get('user_id', '')
                turn_count = conversation_context.get('turn_count', 0)
                context_info = f"\n\n对话上下文：用户ID={user_id}，对话轮数={turn_count}"
            
            summary_prompt = f"""
请为以下对话历史生成一个简洁而全面的摘要。

要求：
1. 保留关键话题和重要信息
2. 记录用户的问题、需求和偏好
3. 记录重要的结论、建议和解决方案
4. 保留用户表达的情感态度
5. 控制在{self.max_summary_length}字以内
6. 使用第三人称描述
7. 突出对话的核心价值

{context_info}

对话历史：
{history_text}

请生成摘要：
"""
            
            # 调用AI服务生成摘要
            summary = await ai_service.generate_response(
                user_message=summary_prompt,
                intent="normal",
                file_content=None,
                web_content=None,
                search_results=None,
                user_identity={},
                contextual_prompt="",
                short_term_context=""
            )
            
            # 清理和截断摘要
            summary = summary.strip()
            if len(summary) > self.max_summary_length:
                summary = summary[:self.max_summary_length] + "..."
            
            app_logger.info(f"AI摘要生成成功，原始消息数: {len(messages)}, 摘要长度: {len(summary)}")
            return summary
            
        except Exception as e:
            app_logger.error(f"AI摘要生成失败: {e}")
            return await self._generate_fallback_summary(messages)
    
    async def _generate_fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成降级摘要"""
        try:
            # 简单的关键词提取和统计
            user_messages = [msg for msg in messages if msg['role'] == 'user']
            assistant_messages = [msg for msg in messages if msg['role'] == 'assistant']
            
            # 提取用户主要话题
            user_topics = []
            for msg in user_messages:
                content = msg['content'][:100]  # 只取前100字符
                if len(content) > 20:  # 过滤太短的消息
                    user_topics.append(content)
            
            # 构建简单摘要
            summary_parts = []
            if user_topics:
                summary_parts.append(f"用户讨论了{len(user_topics)}个话题")
                if len(user_topics) <= 3:
                    summary_parts.extend([f"- {topic}" for topic in user_topics])
                else:
                    summary_parts.extend([f"- {topic}" for topic in user_topics[:3]])
                    summary_parts.append(f"- 等{len(user_topics)-3}个其他话题")
            
            summary_parts.append(f"共{len(messages)}条消息，包含{len(user_messages)}条用户消息和{len(assistant_messages)}条助手回复")
            
            summary = "\n".join(summary_parts)
            app_logger.info(f"降级摘要生成成功: {len(summary)}字符")
            return summary
            
        except Exception as e:
            app_logger.error(f"降级摘要生成失败: {e}")
            return f"[包含 {len(messages)} 条历史消息的对话]"
    
    async def compress_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        conversation_context: Dict[str, Any] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        压缩对话历史
        
        Args:
            conversation_id: 对话ID
            messages: 消息列表
            conversation_context: 对话上下文
            
        Returns:
            (compressed_context, compression_metadata)
        """
        try:
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
                    "summary": None,
                    "compression_ratio": 1.0
                }
            
            # 需要压缩：分离最近对话和历史对话
            recent_count = self.recent_turns * 2  # N轮 = N个用户消息 + N个助手回复
            recent_messages = messages[-recent_count:] if len(messages) > recent_count else messages
            old_messages = messages[:-recent_count] if len(messages) > recent_count else []
            
            # 检查缓存
            cache_key = f"{conversation_id}:{len(old_messages)}"
            summary = self.summary_cache.get(cache_key)
            
            if not summary and old_messages:
                # 生成新的摘要
                app_logger.info(f"为对话 {conversation_id} 生成摘要，旧消息数: {len(old_messages)}")
                summary = await self._generate_ai_summary(old_messages, conversation_context)
                
                # 缓存摘要
                self.summary_cache[cache_key] = summary
                
                # 限制缓存大小
                if len(self.summary_cache) > self.cache_max_size:
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
            
            # 计算压缩统计
            compressed_tokens = self._count_tokens(context)
            compression_ratio = compressed_tokens / total_tokens if total_tokens > 0 else 1.0
            
            # 检查压缩效果
            if compression_ratio > (1 - self.min_compression_ratio):
                app_logger.warning(f"压缩效果不佳，压缩比: {compression_ratio:.2f}")
            
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
                "summary": summary,
                "cache_hit": cache_key in self.summary_cache
            }
            
        except Exception as e:
            app_logger.error(f"对话压缩失败: {e}")
            # 降级：返回空上下文
            return "", {"error": str(e), "compressed": False}
    
    async def batch_compress_conversations(
        self,
        conversations: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量压缩对话"""
        try:
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def compress_single(conv_data):
                async with semaphore:
                    conversation_id = conv_data['conversation_id']
                    messages = conv_data['messages']
                    context = conv_data.get('context', {})
                    
                    compressed_context, metadata = await self.compress_conversation(
                        conversation_id, messages, context
                    )
                    
                    return {
                        'conversation_id': conversation_id,
                        'compressed_context': compressed_context,
                        'metadata': metadata
                    }
            
            # 并发处理
            tasks = [compress_single(conv_data) for conv_data in conversations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    app_logger.error(f"批量压缩第{i}个对话失败: {result}")
                else:
                    valid_results.append(result)
            
            app_logger.info(f"批量压缩完成: {len(valid_results)}/{len(conversations)}")
            return valid_results
            
        except Exception as e:
            app_logger.error(f"批量压缩失败: {e}")
            return []
    
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
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.summary_cache),
            "max_size": self.cache_max_size,
            "cache_keys": list(self.summary_cache.keys())[:10]  # 只显示前10个
        }


# 全局实例
compression_service = CompressionService()
