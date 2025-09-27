"""
日志工具模块
提供统一的日志记录功能
"""
import os
import sys
from loguru import logger
from typing import Optional
from config import settings


class LoggerManager:
    """日志管理器"""
    
    def __init__(self):
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """配置日志器"""
        # 移除默认处理器
        logger.remove()
        
        # 控制台输出
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True
        )
        
        # 创建日志目录
        os.makedirs("logs", exist_ok=True)
        
        # 应用日志文件
        logger.add(
            "logs/app.log",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8"
        )
        
        # 错误日志文件
        logger.add(
            "logs/error.log",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8"
        )
    
    def get_logger(self, name: Optional[str] = None):
        """获取日志器实例"""
        if name:
            return logger.bind(name=name)
        return logger


# 全局日志管理器实例
log_manager = LoggerManager()
app_logger = log_manager.get_logger("chatbot_api")