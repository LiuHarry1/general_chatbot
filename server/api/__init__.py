"""
API路由聚合
统一管理所有API路由
"""
from fastapi import APIRouter
from .v1 import router as v1_router
from .routes import router as legacy_router
from database.api.database_routes import router as database_router

# 创建主路由器
router = APIRouter()

# 注册API版本路由
router.include_router(v1_router, prefix="/v1")

# 注册旧版路由（兼容性）
router.include_router(legacy_router, prefix="")

# 注册数据库路由
router.include_router(database_router, prefix="/db", tags=["database"])

__all__ = ['router']