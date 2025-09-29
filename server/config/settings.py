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
    react_app_api_url: str = os.getenv("REACT_APP_API_URL", "http://localhost:3001/api")
    
    # 文件上传配置
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    allowed_file_types: List[str] = [".pdf", ".txt", ".doc", ".docx", ".md"]
    upload_temp_dir: str = os.getenv("UPLOAD_TEMP_DIR", "temp_uploads")
    
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
    
    # Redis配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    # Qdrant配置
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "chatbot_memory")
    
    # 记忆系统配置
    memory_max_conversations: int = int(os.getenv("MEMORY_MAX_CONVERSATIONS", "5"))
    memory_max_tokens: int = int(os.getenv("MEMORY_MAX_TOKENS", "8000"))
    memory_compression_method: str = os.getenv("MEMORY_COMPRESSION_METHOD", "llm_summary")
    
    # 嵌入配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v1")
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    embedding_timeout: int = int(os.getenv("EMBEDDING_TIMEOUT", "30"))
    
    # 缓存过期时间（秒）
    conversation_ttl: int = int(os.getenv("CONVERSATION_TTL", str(3600 * 24)))  # 24小时
    user_context_ttl: int = int(os.getenv("USER_CONTEXT_TTL", str(3600 * 24 * 7)))  # 7天
    message_ttl: int = int(os.getenv("MESSAGE_TTL", str(3600 * 12)))  # 12小时
    
    class Config:
        env_file = "../.env"
        case_sensitive = False


# 全局配置实例
settings = Settings()
