"""
对话API路由
提供对话的CRUD操作
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database.repositories.conversation_repository import ConversationRepository
from database.connection import DatabaseManager
from models import ConversationCreate, ConversationResponse
from utils.logger import app_logger

# 创建路由器
router = APIRouter(prefix="/conversations", tags=["对话"])

# 初始化数据库管理器
db_manager = DatabaseManager()
conversation_repo = ConversationRepository(db_manager)


@router.post("", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreate):
    """创建新对话"""
    try:
        app_logger.info(f"创建对话: {request.title}")
        
        conversation_id = conversation_repo.create_conversation(
            title=request.title,
            user_id=request.user_id
        )
        
        # 获取创建的对话信息
        created_conversation = conversation_repo.get_conversation(conversation_id)
        if not created_conversation:
            raise HTTPException(status_code=500, detail="对话创建失败")
        
        return ConversationResponse(**created_conversation)
        
    except Exception as e:
        app_logger.error("创建对话失败: {}", e)
        raise HTTPException(status_code=500, detail="创建对话失败")


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(user_id: str = Query(default="default_user")):
    """获取用户的对话列表"""
    try:
        app_logger.info(f"获取用户对话列表: {user_id}")
        
        conversations = conversation_repo.get_conversations(user_id)
        return [ConversationResponse(**conv) for conv in conversations]
        
    except Exception as e:
        app_logger.error("获取对话列表失败: {}", e)
        raise HTTPException(status_code=500, detail="获取对话列表失败")


@router.get("/{conversation_id}", response_model=ConversationResponse)
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
        app_logger.error("获取对话失败: {}", e)
        raise HTTPException(status_code=500, detail="获取对话失败")


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, request: ConversationCreate):
    """更新对话标题"""
    try:
        app_logger.info(f"更新对话: {conversation_id}, 标题: {request.title}")
        
        success = conversation_repo.update_conversation(conversation_id, request.title)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 获取更新后的对话信息
        updated_conversation = conversation_repo.get_conversation(conversation_id)
        if not updated_conversation:
            raise HTTPException(status_code=500, detail="获取更新后的对话失败")
        
        return ConversationResponse(**updated_conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error("更新对话失败: {}", e)
        raise HTTPException(status_code=500, detail="更新对话失败")


@router.delete("/{conversation_id}")
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
        app_logger.error("删除对话失败: {}", e)
        raise HTTPException(status_code=500, detail="删除对话失败")
