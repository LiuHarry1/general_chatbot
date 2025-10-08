# Services Package

# 大语言模型客户端 - 统一API调用
from .model_client import qwen_client

# AI服务 - 业务逻辑层
from .ai_service import ai_service

__all__ = [
    'qwen_client',
    'ai_service'
]

