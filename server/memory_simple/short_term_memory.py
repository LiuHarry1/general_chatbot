"""
短期记忆管理器
简化的对话历史管理实现
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import tiktoken
import httpx

from config import settings

logger = logging.getLogger(__name__)


class ShortTermMemoryManager:
    """简化的短期记忆管理器"""
    
    def __init__(self, max_conversations: int = 5, max_tokens: int = 8000):
        self.max_conversations = max_conversations
        self.max_tokens = max_tokens
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
        self.api_key = settings.dashscope_api_key
        self.llm_model = settings.qwen_model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info(f"ShortTermMemoryManager initialized: max_conv={max_conversations}, max_tokens={max_tokens}")

    def _count_tokens(self, text: str) -> int:
        """计算文本的Token数量"""
        return len(self.tokenizer.encode(text))

    async def _call_llm_for_summary(self, conversation_history: List[Dict[str, Any]]) -> str:
        """调用LLM总结对话历史"""
        if not self.api_key:
            logger.error("Dashscope API key is not set for LLM summary.")
            return "LLM API key not configured for summarization."

        # 构建对话历史文本
        history_text = ""
        for conv in conversation_history:
            history_text += f"用户: {conv.get('user_message', '')}\n"
            history_text += f"AI: {conv.get('ai_response', '')}\n\n"

        prompt_messages = [
            {"role": "system", "content": "你是一个专业的对话总结助手。请将以下对话历史总结成简洁的要点，保留重要信息和上下文。"},
            {"role": "user", "content": f"请总结以下对话历史：\n\n{history_text}"}
        ]
        
        payload = {
            "model": self.llm_model,
            "input": {"messages": prompt_messages},
            "parameters": {
                "temperature": 0.3,
                "result_format": "message"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"LLM summary call failed: {e}")
            return "对话总结失败"

    def build_conversation_context(self, user_id: str) -> str:
        """构建对话上下文"""
        if user_id not in self.conversations:
            return ""
        
        user_conversations = self.conversations[user_id]
        if not user_conversations:
            return ""
        
        context_parts = ["\n\n以下是最近的对话历史，请参考这些上下文："]
        
        for conv in user_conversations[-self.max_conversations:]:
            context_parts.append(f"用户: {conv.get('user_message', '')}")
            context_parts.append(f"AI: {conv.get('ai_response', '')}")
        
        return "\n".join(context_parts)

    async def compress_conversations_if_needed(self, user_id: str) -> Tuple[bool, str]:
        """检查并压缩对话历史"""
        if user_id not in self.conversations:
            return False, ""
        
        user_conversations = self.conversations[user_id]
        if len(user_conversations) <= self.max_conversations:
            return False, ""
        
        # 计算当前Token数
        total_text = ""
        for conv in user_conversations:
            total_text += conv.get('user_message', '') + " " + conv.get('ai_response', '')
        
        current_tokens = self._count_tokens(total_text)
        
        if current_tokens <= self.max_tokens:
            return False, ""
        
        # 需要压缩
        logger.info(f"Compressing conversations for user {user_id}: {len(user_conversations)} conversations, {current_tokens} tokens")
        
        # 保留最新的对话
        recent_conversations = user_conversations[-self.max_conversations:]
        old_conversations = user_conversations[:-self.max_conversations]
        
        # 总结旧对话
        summary = await self._call_llm_for_summary(old_conversations)
        
        # 创建总结对话
        summary_conversation = {
            'user_message': '对话历史总结',
            'ai_response': summary,
            'timestamp': datetime.now().isoformat(),
            'intent': 'summary',
            'sources': []
        }
        
        # 更新对话历史
        self.conversations[user_id] = [summary_conversation] + recent_conversations
        
        logger.info(f"Conversation compression completed for user {user_id}")
        return True, summary

    def add_conversation(self, user_id: str, user_message: str, ai_response: str, 
                        intent: str = "normal", sources: List[str] = None):
        """添加对话到短期记忆"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        conversation = {
            'user_message': user_message,
            'ai_response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'intent': intent,
            'sources': sources or []
        }
        
        self.conversations[user_id].append(conversation)
        
        # 限制对话数量
        if len(self.conversations[user_id]) > self.max_conversations * 2:
            self.conversations[user_id] = self.conversations[user_id][-self.max_conversations:]
        
        logger.debug(f"Added conversation for user {user_id}: {len(self.conversations[user_id])} total conversations")

    def get_conversation_history(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """获取对话历史"""
        if user_id not in self.conversations:
            return []
        
        conversations = self.conversations[user_id]
        if limit:
            return conversations[-limit:]
        return conversations

    def get_recent_conversations(self, user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取最近的对话记录"""
        return self.get_conversation_history(user_id, limit=limit)

    def clear_conversations(self, user_id: str):
        """清空用户对话历史"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"Cleared conversations for user {user_id}")

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户对话统计信息"""
        if user_id not in self.conversations:
            return {"total_conversations": 0, "total_tokens": 0}
        
        conversations = self.conversations[user_id]
        total_text = ""
        for conv in conversations:
            total_text += conv.get('user_message', '') + " " + conv.get('ai_response', '')
        
        return {
            "total_conversations": len(conversations),
            "total_tokens": self._count_tokens(total_text),
            "last_conversation": conversations[-1]['timestamp'] if conversations else None
        }


# 创建全局实例
short_term_memory = ShortTermMemoryManager()
