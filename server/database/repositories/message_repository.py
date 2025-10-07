"""
消息数据仓储
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import logging

from ..connection import DatabaseManager

logger = logging.getLogger(__name__)

class MessageRepository:
    """消息数据访问层"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_message(self, conversation_id: str, role: str, content: str, 
                      intent: str = None, sources: List[str] = None, 
                      attachments: List[Dict] = None, is_typing: bool = False) -> str:
        """创建新消息"""
        import time
        import random
        import uuid
        
        # 使用UUID + 时间戳确保唯一性
        timestamp = int(time.time() * 1000000)  # 微秒级时间戳
        uuid_short = str(uuid.uuid4())[:8]  # UUID前8位
        message_id = f"msg_{timestamp}_{uuid_short}"
        
        # 序列化复杂字段
        sources_json = json.dumps(sources) if sources else None
        attachments_json = json.dumps(attachments) if attachments else None
        
        query = """
            INSERT INTO messages (id, conversation_id, role, content, intent, sources, attachments, is_typing, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        self.db.execute_update(query, (
            message_id, conversation_id, role, content, intent,
            sources_json, attachments_json, is_typing, now
        ))
        
        logger.info(f"创建消息: {message_id}")
        return message_id
    
    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的所有消息"""
        query = """
            SELECT id, conversation_id, role, content, intent, sources, attachments, is_typing, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """
        
        results = self.db.execute_query(query, (conversation_id,))
        
        # 反序列化复杂字段
        for result in results:
            if result['sources']:
                try:
                    result['sources'] = json.loads(result['sources'])
                except:
                    result['sources'] = []
            
            if result['attachments']:
                try:
                    result['attachments'] = json.loads(result['attachments'])
                except:
                    result['attachments'] = []
        
        return results
    
    def update_message(self, message_id: str, **updates) -> bool:
        """更新消息"""
        # 构建动态更新语句
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key == 'sources' and isinstance(value, list):
                set_clauses.append(f"{key} = ?")
                params.append(json.dumps(value))
            elif key == 'attachments' and isinstance(value, list):
                set_clauses.append(f"{key} = ?")
                params.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        query = f"UPDATE messages SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(message_id)
        
        affected = self.db.execute_update(query, tuple(params))
        return affected > 0
    
    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        query = "DELETE FROM messages WHERE id = ?"
        affected = self.db.execute_update(query, (message_id,))
        return affected > 0
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取单个消息"""
        query = """
            SELECT id, conversation_id, role, content, intent, sources, attachments, is_typing, created_at
            FROM messages
            WHERE id = ?
        """
        
        results = self.db.execute_query(query, (message_id,))
        if not results:
            return None
        
        result = results[0]
        
        # 反序列化复杂字段
        if result['sources']:
            try:
                result['sources'] = json.loads(result['sources'])
            except:
                result['sources'] = []
        
        if result['attachments']:
            try:
                result['attachments'] = json.loads(result['attachments'])
            except:
                result['attachments'] = []
        
        return result
