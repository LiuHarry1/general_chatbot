"""
记忆系统API路由
包含长期记忆和短期记忆功能
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from memory_simple import default_memory_manager as memory_manager
from memory_simple.short_term_memory import short_term_memory
from utils.logger import app_logger

# 创建路由器
router = APIRouter()


# 请求/响应模型
class ConversationSummaryRequest(BaseModel):
    conversation_id: str
    summary: str
    metadata: Dict[str, Any]


class SearchContextRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    limit: int = 5


class StoreIdentityRequest(BaseModel):
    user_id: str
    identity_info: Dict[str, Any]


class ExtractIdentityRequest(BaseModel):
    message: str
    user_id: str = "default_user"


@router.post("/store-conversation-summary")
async def store_conversation_summary(request: ConversationSummaryRequest):
    """存储对话摘要到长期记忆"""
    try:
        app_logger.info(f"存储对话摘要: {request.conversation_id}")
        doc_id = await memory_manager.store_conversation_summary(
            conversation_id=request.conversation_id,
            summary=request.summary,
            metadata=request.metadata
        )
        if doc_id:
            return {"success": True, "document_id": doc_id, "message": "对话摘要存储成功"}
        raise HTTPException(status_code=500, detail="对话摘要存储失败")
    except Exception as e:
        app_logger.error(f"存储对话摘要失败: {e}")
        raise HTTPException(status_code=500, detail="存储对话摘要失败")


@router.post("/search-context")
async def search_context(request: SearchContextRequest):
    """搜索相关上下文"""
    try:
        app_logger.info(f"搜索相关上下文: {request.query[:50]}...")
        results = await memory_manager.search_relevant_context(
            query=request.query,
            user_id=request.user_id,
            limit=request.limit
        )
        return {"success": True, "results": results, "message": "相关上下文搜索成功"}
    except Exception as e:
        app_logger.error(f"搜索相关上下文失败: {e}")
        raise HTTPException(status_code=500, detail="搜索相关上下文失败")


@router.post("/store-user-identity")
async def store_user_identity(request: StoreIdentityRequest):
    """存储用户身份信息"""
    try:
        app_logger.info(f"存储用户身份信息: {request.user_id}")
        success = await memory_manager.store_user_identity(
            user_id=request.user_id,
            identity_info=request.identity_info
        )
        if success:
            return {"success": True, "message": "用户身份信息存储成功"}
        raise HTTPException(status_code=500, detail="用户身份信息存储失败")
    except Exception as e:
        app_logger.error(f"存储用户身份信息失败: {e}")
        raise HTTPException(status_code=500, detail="存储用户身份信息失败")


@router.post("/extract-identity")
async def extract_identity_from_message(request: ExtractIdentityRequest):
    """从消息中提取身份信息"""
    try:
        app_logger.info(f"提取身份信息: {request.message[:50]}...")
        identity_info = await memory_manager.extract_identity_from_message(
            message=request.message,
            user_id=request.user_id
        )
        return {
            "success": True,
            "identity_info": identity_info,
            "message": "身份信息提取成功" if identity_info else "未检测到身份信息"
        }
    except Exception as e:
        app_logger.error(f"提取身份信息失败: {e}")
        raise HTTPException(status_code=500, detail="提取身份信息失败")


@router.get("/user-identity/{user_id}")
async def get_user_identity(user_id: str):
    """获取用户身份信息"""
    try:
        app_logger.info(f"获取用户身份: {user_id}")
        identity_info = await memory_manager.get_user_identity(user_id)
        return {
            "success": True,
            "identity_info": identity_info,
            "message": "用户身份信息获取成功"
        }
    except Exception as e:
        app_logger.error(f"获取用户身份失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户身份失败")


@router.get("/short-term/stats/{user_id}")
async def get_short_term_stats(user_id: str):
    """获取短期记忆统计信息"""
    try:
        app_logger.info(f"获取短期记忆统计: {user_id}")
        stats = short_term_memory.get_stats(user_id)
        return {
            "success": True,
            "stats": stats,
            "message": "短期记忆统计信息获取成功"
        }
    except Exception as e:
        app_logger.error(f"获取短期记忆统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取短期记忆统计失败")


@router.delete("/short-term/clear/{user_id}")
async def clear_short_term_memory(user_id: str):
    """清空用户短期记忆"""
    try:
        app_logger.info(f"清空短期记忆: {user_id}")
        short_term_memory.clear_conversations(user_id)
        return {
            "success": True,
            "message": "短期记忆清空成功"
        }
    except Exception as e:
        app_logger.error(f"清空短期记忆失败: {e}")
        raise HTTPException(status_code=500, detail="清空短期记忆失败")


@router.get("/health")
async def memory_health_check():
    """记忆系统健康检查"""
    try:
        health_status = await memory_manager.health_check()
        return {
            "success": True,
            "status": health_status,
            "message": "记忆系统健康检查完成"
        }
    except Exception as e:
        app_logger.error(f"记忆系统健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="记忆系统健康检查失败")
