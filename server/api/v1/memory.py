"""
记忆管理API
提供记忆系统的REST API接口
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from memory.modern_memory_manager import modern_memory_manager
from memory.profile_service import profile_service
from memory.semantic_search import semantic_search_service
from memory.compression_service import compression_service

router = APIRouter(prefix="/memory", tags=["memory"])


# 请求模型
class ProcessConversationRequest(BaseModel):
    user_id: str
    conversation_id: str
    message: str
    response: str
    intent: str
    sources: Optional[List[str]] = None


class SearchMemoriesRequest(BaseModel):
    query: str
    user_id: str
    memory_types: Optional[List[str]] = None
    limit: Optional[int] = 10


class UpdateProfileRequest(BaseModel):
    user_id: str
    preferences: Optional[Dict[str, Any]] = None
    identity: Optional[Dict[str, Any]] = None


# 响应模型
class MemoryResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    total: int
    query: str


@router.post("/process", response_model=MemoryResponse)
async def process_conversation(request: ProcessConversationRequest):
    """处理对话，更新记忆系统"""
    try:
        result = await modern_memory_manager.process_conversation(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            message=request.message,
            response=request.response,
            intent=request.intent,
            sources=request.sources
        )
        
        return MemoryResponse(
            success=result["success"],
            data=result,
            message=result.get("message", "Memory processing completed")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process conversation: {str(e)}")


@router.get("/context/{user_id}/{conversation_id}")
async def get_conversation_context(
    user_id: str,
    conversation_id: str,
    current_message: str = Query(..., description="Current user message"),
    limit: int = Query(5, description="Number of memories to retrieve")
):
    """获取对话上下文"""
    try:
        context, metadata = await modern_memory_manager.get_conversation_context(
            user_id=user_id,
            conversation_id=conversation_id,
            current_message=current_message,
            limit=limit
        )
        
        return {
            "success": True,
            "context": context,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_memories(request: SearchMemoriesRequest):
    """搜索记忆"""
    try:
        results = await modern_memory_manager.search_memories(
            query=request.query,
            user_id=request.user_id,
            memory_types=request.memory_types,
            limit=request.limit
        )
        
        return SearchResponse(
            success=True,
            results=results,
            total=len(results),
            query=request.query
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """获取用户画像"""
    try:
        profile = await profile_service.get_user_profile(user_id)
        
        return {
            "success": True,
            "profile": profile
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.post("/profile/update")
async def update_user_profile(request: UpdateProfileRequest):
    """更新用户画像"""
    try:
        # 构建更新数据
        update_data = {}
        if request.preferences:
            update_data["preferences"] = request.preferences
        if request.identity:
            update_data["identity"] = request.identity
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        # 更新用户偏好
        success = await profile_service.profile_service.update_user_preferences(
            user_id=request.user_id,
            preferences=update_data
        )
        
        return {
            "success": success,
            "message": "Profile updated successfully" if success else "Failed to update profile"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.get("/insights/{user_id}")
async def get_user_insights(user_id: str):
    """获取用户洞察"""
    try:
        insights = await modern_memory_manager.get_user_insights(user_id)
        
        return {
            "success": True,
            "insights": insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user insights: {str(e)}")


@router.get("/search/suggestions/{user_id}")
async def get_search_suggestions(
    user_id: str,
    query: str = Query("", description="Partial search query"),
    limit: int = Query(5, description="Number of suggestions")
):
    """获取搜索建议"""
    try:
        suggestions = await semantic_search_service.get_search_suggestions(
            user_id=user_id,
            partial_query=query,
            limit=limit
        )
        
        return {
            "success": True,
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/timeline/{user_id}")
async def get_memory_timeline(
    user_id: str,
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(20, description="Number of memories to retrieve")
):
    """获取记忆时间线"""
    try:
        timeline = await semantic_search_service.get_memory_timeline(
            user_id=user_id,
            days=days,
            limit=limit
        )
        
        return {
            "success": True,
            "timeline": timeline,
            "days": days,
            "total": len(timeline)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


@router.post("/compress/{conversation_id}")
async def compress_conversation(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
):
    """压缩对话历史"""
    try:
        compressed_context, metadata = await compression_service.compress_conversation(
            conversation_id=conversation_id,
            messages=messages,
            conversation_context=context
        )
        
        return {
            "success": True,
            "compressed_context": compressed_context,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compress conversation: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        health = await modern_memory_manager.health_check()
        
        return {
            "success": True,
            "health": health
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "health": {"status": "error"}
        }


@router.post("/cleanup")
async def cleanup_old_memories(
    days: int = Query(30, description="Number of days to keep memories")
):
    """清理旧记忆"""
    try:
        deleted_count = await modern_memory_manager.cleanup_old_memories(days=days)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old memories"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup memories: {str(e)}")


@router.get("/stats/{user_id}")
async def get_user_memory_stats(user_id: str):
    """获取用户记忆统计"""
    try:
        stats = await modern_memory_manager.redis_manager.get_user_memory_stats(user_id)
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory stats: {str(e)}")


@router.delete("/profile/{user_id}")
async def clear_user_data(user_id: str):
    """清除用户所有数据"""
    try:
        success = await modern_memory_manager.redis_manager.clear_user_data(user_id)
        
        return {
            "success": success,
            "message": "User data cleared successfully" if success else "Failed to clear user data"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear user data: {str(e)}")

