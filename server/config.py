"""
配置文件
包含所有配置项和常量定义
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # API密钥
    dashscope_api_key: str = "sk-f256c03643e9491fb1ebc278dd958c2d"
    tavily_api_key: str = "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"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 3001
    debug: bool = True
    
    # 文件上传配置
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [".pdf", ".txt", ".doc", ".docx", ".md"]
    upload_temp_dir: str = "temp_uploads"
    
    # 内容长度限制
    max_content_length: int = 8000
    max_web_content_length: int = 4000
    
    # 搜索配置
    tavily_max_results: int = 5
    tavily_search_depth: str = "basic"
    
    # 日志配置
    log_level: str = "INFO"
    log_rotation: str = "1 day"
    log_retention: str = "7 days"
    
    # 通义千问配置
    qwen_model: str = "qwen-turbo"
    qwen_temperature: float = 0.7
    qwen_max_tokens: int = 3000
    qwen_top_p: float = 0.8
    qwen_repetition_penalty: float = 1.1
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()

# 搜索关键词配置
SEARCH_KEYWORDS = [
    # 英文关键词
    "search", "find", "look up", "what is", "how to", "where is",
    "latest", "news", "information", "update", "current", "recent",
    "top", "best", "trending", "popular", "entertainment", "sports",
    "technology", "business", "world", "today", "this week", "this month",
    
    # 中文关键词
    "搜索", "查找", "寻找", "什么是", "如何", "哪里", 
    "最新", "新闻", "资讯", "更新", "当前", "现在", "最近",
    "top", "排行", "热门", "娱乐", "体育", "科技", "商业", 
    "世界", "今天", "本周", "本月", "提供", "给我", "推荐"
]

# 用户代理字符串
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# API端点路径
API_PREFIX = "/api"
HEALTH_ENDPOINT = f"{API_PREFIX}/health"
STATUS_ENDPOINT = f"{API_PREFIX}/status"
CHAT_ENDPOINT = f"{API_PREFIX}/chat"
UPLOAD_ENDPOINT = f"{API_PREFIX}/upload"
ANALYZE_URL_ENDPOINT = f"{API_PREFIX}/analyze-url"
SUPPORTED_FORMATS_ENDPOINT = f"{API_PREFIX}/supported-formats"

