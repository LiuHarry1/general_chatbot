"""
API v1 路由聚合
按功能分组的路由模块
"""
from fastapi import APIRouter
from .chat import router as chat_router
from .memory import router as memory_router
from .files import router as files_router
from .health import router as health_router
from .database import router as database_router
from .images import router as images_router

# 创建v1路由器
router = APIRouter()

# 注册子路由
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(memory_router, prefix="/memory", tags=["memory"])
router.include_router(files_router, prefix="/files", tags=["files"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(database_router, tags=["database"])
router.include_router(images_router, prefix="/images", tags=["images"])

__all__ = ['router']
