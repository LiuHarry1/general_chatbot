"""
对话数据仓储
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ..connection import DatabaseManager

logger = logging.getLogger(__name__)

class ConversationRepository:
    """对话数据访问层"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_conversation(self, title: str, user_id: str = "default_user") -> str:
        """创建新对话"""
        import time
        import uuid
        
        # 使用UUID + 时间戳确保唯一性
        timestamp = int(time.time() * 1000000)  # 微秒级时间戳
        uuid_short = str(uuid.uuid4())[:8]  # UUID前8位
        conversation_id = f"conv_{timestamp}_{uuid_short}"
        
        query = """
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        self.db.execute_update(query, (conversation_id, user_id, title, now, now))
        
        logger.info(f"创建对话: {conversation_id}")
        return conversation_id
    
    def get_conversations(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """获取用户的对话列表，包含最后消息信息"""
        query = """
            SELECT 
                c.id, 
                c.title, 
                c.created_at, 
                c.updated_at,
                COALESCE(m.content, '') as last_message,
                COALESCE(m.created_at, c.created_at) as last_message_time,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN (
                SELECT conversation_id, MAX(created_at) as max_time
                FROM messages
                GROUP BY conversation_id
            ) latest ON c.id = latest.conversation_id AND m.created_at = latest.max_time
            WHERE c.user_id = ?
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """
        
        results = self.db.execute_query(query, (user_id,))
        return results
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取单个对话"""
        query = """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = ?
        """
        
        results = self.db.execute_query(query, (conversation_id,))
        return results[0] if results else None
    
    def update_conversation(self, conversation_id: str, title: str) -> bool:
        """更新对话标题"""
        query = """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
        """
        
        now = datetime.now().isoformat()
        affected = self.db.execute_update(query, (title, now, conversation_id))
        return affected > 0
    
    def get_current_conversation_messages(self, conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取当前对话的已完成消息历史，用于意图识别（排除当前用户的问题）"""
        try:
            query = """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """
            messages = self.db.execute_query(query, (conversation_id,))
            
            # 转换为用于意图识别的格式，只包含已完成的对话对
            result = []
            for i in range(len(messages) - 1):
                if messages[i]['role'] == 'user' and messages[i + 1]['role'] == 'assistant':
                    result.append({
                        'user_message': messages[i]['content'],
                        'ai_response': messages[i + 1]['content']
                    })
            
            # 限制返回的对话对数量，最多返回最近N个对话对
            return result[-limit:] if limit > 0 else result
            
        except Exception as e:
            logger.error(f"获取当前对话消息失败: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话及其所有消息"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除附件
                cursor.execute("DELETE FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = ?)", (conversation_id,))
                
                # 删除消息
                cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                
                # 删除对话
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                
                conn.commit()
                logger.info(f"删除对话: {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            return False
