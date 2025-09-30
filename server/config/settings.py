"""
应用主配置
包含所有配置项和环境变量处理
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用主配置"""
    
    # API密钥配置
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "sk-f256c03643e9491fb1ebc278dd958c2d")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "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")
    
    # 服务器配置
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "3001"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # 文件上传配置
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    allowed_file_types: List[str] = [".pdf", ".txt", ".doc", ".docx", ".md"]
    
    # 内容长度限制
    max_content_length: int = int(os.getenv("MAX_CONTENT_LENGTH", "8000"))
    max_web_content_length: int = int(os.getenv("MAX_WEB_CONTENT_LENGTH", "4000"))
    
    # 搜索配置
    tavily_max_results: int = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
    tavily_search_depth: str = os.getenv("TAVILY_SEARCH_DEPTH", "basic")
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_rotation: str = os.getenv("LOG_ROTATION", "1 day")
    log_retention: str = os.getenv("LOG_RETENTION", "7 days")
    
    # 通义千问配置
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen-turbo")
    qwen_temperature: float = float(os.getenv("QWEN_TEMPERATURE", "0.7"))
    qwen_max_tokens: int = int(os.getenv("QWEN_MAX_TOKENS", "3000"))
    qwen_top_p: float = float(os.getenv("QWEN_TOP_P", "0.8"))
    qwen_repetition_penalty: float = float(os.getenv("QWEN_REPETITION_PENALTY", "1.1"))
    
    class Config:
        env_file = "../.env"
        case_sensitive = False


# 全局配置实例
settings = Settings()
