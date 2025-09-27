"""
AI聊天机器人API主程序
基于FastAPI构建的高性能后端服务
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime

# 导入配置和路由
from config import settings
from api.routes import router
from utils.logger import app_logger
from models import ErrorResponse


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    # 创建FastAPI实例
    app = FastAPI(
        title="AI Chatbot API",
        description="基于通义千问和Tavily搜索的AI聊天机器人API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router, prefix="/api")
    
    # 全局异常处理
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理"""
        app_logger.error(f"请求验证失败: {exc}")
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="请求参数错误",
                message="请求参数格式不正确",
                timestamp=datetime.now().isoformat(),
                details={"errors": exc.errors()}
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        app_logger.error(f"未处理的异常: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="服务器内部错误",
                message="处理请求时发生未知错误",
                timestamp=datetime.now().isoformat()
            ).dict()
        )
    
    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        app_logger.info("AI聊天机器人API启动中...")
        app_logger.info(f"服务配置: {settings.host}:{settings.port}")
        app_logger.info(f"调试模式: {settings.debug}")
        app_logger.info("API文档地址: http://localhost:3001/docs")
        app_logger.info("AI聊天机器人API启动完成")
    
    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        app_logger.info("AI聊天机器人API正在关闭...")
        app_logger.info("AI聊天机器人API已关闭")
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )