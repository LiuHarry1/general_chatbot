"""
API v1 路由聚合
按功能分组的路由模块
"""
from fastapi import APIRouter
from .chat import router as chat_router
from .files import router as files_router
from .health import router as health_router
from .conversations import router as conversations_router
from .messages import router as messages_router
from .images import router as images_router

# 创建v1路由器
router = APIRouter()

# 注册子路由
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(files_router, prefix="/files", tags=["files"])
router.include_router(health_router, tags=["health"])
router.include_router(conversations_router, prefix="/db", tags=["对话"])
router.include_router(messages_router, prefix="/db", tags=["消息"])
router.include_router(images_router, prefix="/images", tags=["images"])

__all__ = ['router']
