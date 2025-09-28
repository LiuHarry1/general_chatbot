"""
常量定义
包含应用中使用的所有常量
"""
from enum import Enum


class IntentType(Enum):
    """意图类型枚举"""
    NORMAL = "normal"
    FILE = "file"
    WEB = "web"
    SEARCH = "search"


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"


class AttachmentType(Enum):
    """附件类型枚举"""
    FILE = "file"
    URL = "url"


# API端点路径
class APIPaths:
    """API端点路径常量"""
    PREFIX = "/api"
    V1_PREFIX = f"{PREFIX}/v1"
    HEALTH = f"{PREFIX}/health"
    STATUS = f"{PREFIX}/status"
    CHAT = f"{V1_PREFIX}/chat"
    CHAT_STREAM = f"{V1_PREFIX}/chat/stream"
    UPLOAD = f"{V1_PREFIX}/files/upload"
    ANALYZE_URL = f"{V1_PREFIX}/files/analyze-url"
    SUPPORTED_FORMATS = f"{V1_PREFIX}/files/supported-formats"


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


# 文件类型配置
class FileConfig:
    """文件配置常量"""
    MAX_SIZE_MB = 10
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
    ALLOWED_TYPES = [".pdf", ".txt", ".doc", ".docx", ".md"]
    TEMP_DIR = "temp_uploads"


# 内容长度限制
class ContentLimits:
    """内容长度限制常量"""
    MAX_CONTENT_LENGTH = 8000
    MAX_WEB_CONTENT_LENGTH = 4000


# 通义千问配置
class QwenConfig:
    """通义千问配置常量"""
    DEFAULT_MODEL = "qwen-turbo"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 3000
    DEFAULT_TOP_P = 0.8
    DEFAULT_REPETITION_PENALTY = 1.1


# 搜索配置
class SearchConfig:
    """搜索配置常量"""
    TAVILY_MAX_RESULTS = 5
    TAVILY_SEARCH_DEPTH = "basic"


# 日志配置
class LogConfig:
    """日志配置常量"""
    DEFAULT_LEVEL = "INFO"
    DEFAULT_ROTATION = "1 day"
    DEFAULT_RETENTION = "7 days"


# 记忆系统配置
class MemoryConfig:
    """记忆系统配置常量"""
    DEFAULT_MAX_CONVERSATIONS = 5
    DEFAULT_MAX_TOKENS = 8000
    DEFAULT_COMPRESSION_METHOD = "llm_summary"


# Redis配置
class RedisConfig:
    """Redis配置常量"""
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6379
    DEFAULT_DB = 0
    DEFAULT_TTL = 3600 * 24  # 24小时


# Qdrant配置
class QdrantConfig:
    """Qdrant配置常量"""
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6333
    DEFAULT_COLLECTION = "chatbot_memory"
    DEFAULT_VECTOR_SIZE = 1536
