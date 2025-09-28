"""
数据库仓储层
提供数据访问的抽象接口
"""

from .conversation_repository import ConversationRepository
from .message_repository import MessageRepository

__all__ = ['ConversationRepository', 'MessageRepository']
