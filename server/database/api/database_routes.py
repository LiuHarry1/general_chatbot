"""
数据库API路由
提供对话和消息的CRUD操作
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..repositories.conversation_repository import ConversationRepository
from ..repositories.message_repository import MessageRepository
from ..connection import DatabaseManager
from models import (
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse, MessageUpdate
)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.logger import app_logger

# 创建数据库实例
db_manager = DatabaseManager()
conversation_repo = ConversationRepository(db_manager)
message_repo = MessageRepository(db_manager)

# 创建路由器
router = APIRouter()

# 对话相关API
@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(conversation: ConversationCreate):
    """创建新对话"""
    try:
        app_logger.info(f"创建对话: {conversation.title}")
        
        conversation_id = conversation_repo.create_conversation(
            title=conversation.title,
            user_id=conversation.user_id
        )
        
        # 获取创建的对话信息
        created_conversation = conversation_repo.get_conversation(conversation_id)
        if not created_conversation:
            raise HTTPException(status_code=500, detail="对话创建失败")
        
        return ConversationResponse(**created_conversation)
        
    except Exception as e:
        app_logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail="创建对话失败")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(user_id: str = Query(default="default_user")):
    """获取用户的对话列表"""
    try:
        app_logger.info(f"获取用户对话列表: {user_id}")
        
        conversations = conversation_repo.get_conversations(user_id)
        return [ConversationResponse(**conv) for conv in conversations]
        
    except Exception as e:
        app_logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话列表失败")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """获取单个对话"""
    try:
        app_logger.info(f"获取对话: {conversation_id}")
        
        conversation = conversation_repo.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return ConversationResponse(**conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取对话失败: {e}")
        raise HTTPException(status_code=500, detail="获取对话失败")

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, title: str = Query(...)):
    """更新对话标题"""
    try:
        app_logger.info(f"更新对话: {conversation_id}, 标题: {title}")
        
        success = conversation_repo.update_conversation(conversation_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 获取更新后的对话信息
        updated_conversation = conversation_repo.get_conversation(conversation_id)
        if not updated_conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return ConversationResponse(**updated_conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新对话失败: {e}")
        raise HTTPException(status_code=500, detail="更新对话失败")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    try:
        app_logger.info(f"删除对话: {conversation_id}")
        
        success = conversation_repo.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return {"message": "对话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail="删除对话失败")

# 消息相关API
@router.post("/messages", response_model=MessageResponse)
async def create_message(message: MessageCreate):
    """创建新消息"""
    try:
        app_logger.info(f"创建消息: {message.conversation_id}")
        
        message_id = message_repo.create_message(
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            intent=message.intent,
            sources=message.sources,
            attachments=message.attachments,
            is_typing=message.is_typing
        )
        
        # 获取创建的消息信息
        messages = message_repo.get_messages(message.conversation_id)
        created_message = next((msg for msg in messages if msg['id'] == message_id), None)
        if not created_message:
            raise HTTPException(status_code=500, detail="消息创建失败")
        
        # 映射字段名
        created_message['timestamp'] = created_message['created_at']
        return MessageResponse(**created_message)
        
    except Exception as e:
        app_logger.error(f"创建消息失败: {e}")
        raise HTTPException(status_code=500, detail="创建消息失败")

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(conversation_id: str):
    """获取对话的所有消息"""
    try:
        app_logger.info(f"获取对话消息: {conversation_id}")
        
        messages = message_repo.get_messages(conversation_id)
        # 映射字段名
        for msg in messages:
            msg['timestamp'] = msg['created_at']
        return [MessageResponse(**msg) for msg in messages]
        
    except Exception as e:
        app_logger.error(f"获取消息失败: {e}")
        raise HTTPException(status_code=500, detail="获取消息失败")

@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(message_id: str, message_update: MessageUpdate):
    """更新消息"""
    try:
        app_logger.info(f"更新消息: {message_id}")
        
        # 构建更新数据
        updates = {}
        if message_update.content is not None:
            updates['content'] = message_update.content
        if message_update.intent is not None:
            updates['intent'] = message_update.intent
        if message_update.sources is not None:
            updates['sources'] = message_update.sources
        if message_update.attachments is not None:
            updates['attachments'] = message_update.attachments
        if message_update.is_typing is not None:
            updates['is_typing'] = message_update.is_typing
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
        
        success = message_repo.update_message(message_id, **updates)
        if not success:
            raise HTTPException(status_code=404, detail="消息不存在")
        
        # 获取更新后的消息信息
        # 这里需要从消息中找到对应的conversation_id
        # 简化处理，直接返回更新成功
        return {"message": "消息更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新消息失败: {e}")
        raise HTTPException(status_code=500, detail="更新消息失败")

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str):
    """删除消息"""
    try:
        app_logger.info(f"删除消息: {message_id}")
        
        success = message_repo.delete_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail="消息不存在")
        
        return {"message": "消息删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除消息失败: {e}")
        raise HTTPException(status_code=500, detail="删除消息失败")
