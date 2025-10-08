"""
内存格式化器
负责消息格式化和token计数
"""
from typing import List, Dict, Any
import logging

from utils.logger import app_logger

logger = logging.getLogger(__name__)


class MemoryFormatter:
    """内存格式化器 - 处理消息格式化和token估算"""
    
    def __init__(self):
        app_logger.info("MemoryFormatter initialized")
    
    def count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息的token数量"""
        total_text = ""
        for message in messages:
            total_text += message.get("content", "")
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    def count_tokens_for_messages(self, messages: List[Dict[str, Any]]) -> int:
        """计算消息列表的token数量"""
        total_text = ""
        for msg in messages:
            user_msg = msg.get('user_message', '')
            ai_response = msg.get('ai_response', '')
            total_text += user_msg + ai_response
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    def format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
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
    
    def format_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """格式化对话历史（去重处理）"""
        if not conversations:
            return ""
        
        # 去重处理：使用消息内容作为key
        seen_messages = set()
        unique_conversations = []
        
        for conv in conversations:
            message = conv.get("message", "")
            response = conv.get("response", "")
            
            # 创建消息的唯一标识
            message_key = f"{message}|{response}"
            
            if message_key not in seen_messages:
                seen_messages.add(message_key)
                unique_conversations.append(conv)
        
        app_logger.info(f"📊 [FORMATTER] Filtered {len(conversations)} -> {len(unique_conversations)} unique conversations")
        
        formatted = []
        for conv in unique_conversations:
            timestamp = conv.get("timestamp", "")
            message = conv.get("message", "")
            response = conv.get("response", "")
            
            formatted.append(f"[{timestamp}] 用户: {message}")
            formatted.append(f"[{timestamp}] 助手: {response}")
        
        return "\n".join(formatted)


# 全局实例
memory_formatter = MemoryFormatter()

