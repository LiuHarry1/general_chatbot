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
        conversation_id = f"conv_{int(datetime.now().timestamp() * 1000)}"
        
        query = """
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        self.db.execute_update(query, (conversation_id, user_id, title, now, now))
        
        logger.info(f"创建对话: {conversation_id}")
        return conversation_id
    
    def get_conversations(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """获取用户的对话列表"""
        query = """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
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
