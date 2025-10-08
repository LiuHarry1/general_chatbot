"""
日志工具模块
提供统一的日志记录功能
"""
import os
import sys
import time
import functools
import inspect
from loguru import logger
from typing import Optional, Callable, Any
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


def log_execution_time(func: Callable = None, *, threshold_ms: float = 0, log_args: bool = False) -> Callable:
    """
    记录函数执行时间的装饰器
    
    Args:
        func: 被装饰的函数
        threshold_ms: 只记录超过此阈值（毫秒）的执行时间，0表示记录所有
        log_args: 是否记录函数参数
    
    Examples:
        # 基本用法
        @log_execution_time
        def my_function():
            pass
        
        # 只记录耗时超过100ms的
        @log_execution_time(threshold_ms=100)
        def slow_function():
            pass
        
        # 同时记录参数
        @log_execution_time(log_args=True)
        def process_data(data):
            pass
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs) -> Any:
            func_name = f"{fn.__module__}.{fn.__qualname__}"
            start_time = time.perf_counter()
            
            try:
                result = await fn(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                if elapsed_ms >= threshold_ms:
                    log_msg = f"⏱️ {func_name} took {elapsed_ms:.2f}ms"
                    if log_args and (args or kwargs):
                        args_str = ", ".join([repr(a)[:50] for a in args[:3]])  # 只显示前3个参数
                        if args_str:
                            log_msg += f" | args: {args_str}"
                    app_logger.info(log_msg)
                
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                app_logger.error(f"❌ {func_name} failed after {elapsed_ms:.2f}ms: {e}")
                raise
        
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs) -> Any:
            func_name = f"{fn.__module__}.{fn.__qualname__}"
            start_time = time.perf_counter()
            
            try:
                result = fn(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                if elapsed_ms >= threshold_ms:
                    log_msg = f"⏱️ {func_name} took {elapsed_ms:.2f}ms"
                    if log_args and (args or kwargs):
                        args_str = ", ".join([repr(a)[:50] for a in args[:3]])
                        if args_str:
                            log_msg += f" | args: {args_str}"
                    app_logger.info(log_msg)
                
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                app_logger.error(f"❌ {func_name} failed after {elapsed_ms:.2f}ms: {e}")
                raise
        
        # 判断是否为异步函数
        if inspect.iscoroutinefunction(fn):
            return async_wrapper
        else:
            return sync_wrapper
    
    # 支持 @log_execution_time 和 @log_execution_time() 两种用法
    if func is None:
        return decorator
    else:
        return decorator(func)