"""
API路由聚合
统一管理所有API路由
"""
from fastapi import APIRouter
from .v1 import router as v1_router

# 创建主路由器
router = APIRouter()

# 注册API版本路由（包含数据库路由）
router.include_router(v1_router, prefix="/v1")

__all__ = ['router']