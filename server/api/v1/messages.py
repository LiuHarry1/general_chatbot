"""
消息API路由
提供消息的CRUD操作
"""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.repositories.message_repository import MessageRepository
from database.connection import DatabaseManager
from models import MessageCreate, MessageResponse, MessageUpdate
from utils.logger import app_logger

# 创建路由器
router = APIRouter(prefix="/messages", tags=["消息"])

# 初始化数据库管理器
db_manager = DatabaseManager()
message_repo = MessageRepository(db_manager)


@router.post("", response_model=MessageResponse)
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
        
        return MessageResponse(**created_message)
        
    except Exception as e:
        app_logger.error("创建消息失败: {}", e)
        raise HTTPException(status_code=500, detail="创建消息失败")


@router.get("/conversations/{conversation_id}", response_model=List[MessageResponse])
async def get_messages(conversation_id: str):
    """获取对话的所有消息"""
    try:
        app_logger.info(f"获取对话消息: {conversation_id}")
        
        messages = message_repo.get_messages(conversation_id)
        return [MessageResponse(**msg) for msg in messages]
        
    except Exception as e:
        app_logger.error("获取消息失败: {}", e)
        raise HTTPException(status_code=500, detail="获取消息失败")


@router.put("/{message_id}", response_model=MessageResponse)
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
        updated_message = message_repo.get_message(message_id)
        if not updated_message:
            raise HTTPException(status_code=500, detail="获取更新后的消息失败")
        
        return MessageResponse(**updated_message)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("更新消息失败: {}", e)
        raise HTTPException(status_code=500, detail="更新消息失败")


@router.delete("/{message_id}")
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
        app_logger.error("删除消息失败: {}", e)
        raise HTTPException(status_code=500, detail="删除消息失败")
