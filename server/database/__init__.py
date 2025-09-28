"""
数据库包
包含所有数据库相关的功能：模型、仓储、API等
"""

from .connection import DatabaseManager
from .repositories.conversation_repository import ConversationRepository
from .repositories.message_repository import MessageRepository
from .api.database_routes import router as database_router

# 全局数据库实例
db_manager = DatabaseManager()
conversation_repo = ConversationRepository(db_manager)
message_repo = MessageRepository(db_manager)

__all__ = [
    'DatabaseManager',
    'ConversationRepository', 
    'MessageRepository',
    'database_router',
    'db_manager',
    'conversation_repo',
    'message_repo'
]
