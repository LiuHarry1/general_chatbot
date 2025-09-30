"""
数据库相关模型
用于数据库操作的请求和响应模型
"""
from pydantic import BaseModel
from typing import List, Optional


class ConversationCreate(BaseModel):
    """创建对话的请求模型"""
    title: str
    user_id: str = "default_user"


class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: str
    title: str
    created_at: str
    updated_at: str
    last_message: Optional[str] = None
    last_message_time: Optional[str] = None
    message_count: Optional[int] = 0
    
    class Config:
        json_encoders = {
            # 确保时间格式正确
        }


class MessageCreate(BaseModel):
    """创建消息的请求模型"""
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = None
    sources: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None
    is_typing: bool = False


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = None
    sources: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None
    is_typing: bool = False
    created_at: str  # 统一使用created_at字段名


class MessageUpdate(BaseModel):
    """更新消息的请求模型"""
    content: Optional[str] = None
    intent: Optional[str] = None
    sources: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None
    is_typing: Optional[bool] = None
