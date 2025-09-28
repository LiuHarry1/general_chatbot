"""
数据库API层
提供数据库相关的REST API接口
"""

from .database_routes import router as database_router

__all__ = ['database_router']
