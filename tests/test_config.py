"""
配置测试
测试配置加载和验证
"""
import pytest
import os
from unittest.mock import patch

from server.config import settings
from server.config.constants import (
    IntentType, MessageRole, AttachmentType,
    APIPaths, SEARCH_KEYWORDS, USER_AGENT,
    FileConfig, ContentLimits, QwenConfig
)


class TestSettings:
    """设置测试"""
    
    def test_default_settings(self):
        """测试默认设置"""
        assert settings.host == "0.0.0.0"
        assert settings.port == 3001
        assert settings.debug == True
        assert settings.qwen_model == "qwen-turbo"
        assert settings.qwen_temperature == 0.7
    
    def test_file_upload_settings(self):
        """测试文件上传设置"""
        assert settings.max_file_size == 10 * 1024 * 1024  # 10MB
        assert ".pdf" in settings.allowed_file_types
        assert ".txt" in settings.allowed_file_types
        assert ".doc" in settings.allowed_file_types
        assert ".docx" in settings.allowed_file_types
        assert ".md" in settings.allowed_file_types
    
    def test_content_limits(self):
        """测试内容长度限制"""
        assert settings.max_content_length == 8000
        assert settings.max_web_content_length == 4000
    
    def test_search_settings(self):
        """测试搜索设置"""
        assert settings.tavily_max_results == 5
        assert settings.tavily_search_depth == "basic"
    
    def test_memory_settings(self):
        """测试记忆系统设置"""
        assert settings.memory_max_conversations == 5
        assert settings.memory_max_tokens == 8000
        assert settings.memory_compression_method == "llm_summary"
    
    def test_redis_settings(self):
        """测试Redis设置"""
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
    
    def test_qdrant_settings(self):
        """测试Qdrant设置"""
        assert settings.qdrant_host == "localhost"
        assert settings.qdrant_port == 6333
        assert settings.qdrant_collection_name == "chatbot_memory"
    
    @patch.dict(os.environ, {"PORT": "8080", "DEBUG": "false"})
    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        # 重新导入设置以应用环境变量
        from server.config.settings import Settings
        test_settings = Settings()
        assert test_settings.port == 8080
        assert test_settings.debug == False


class TestConstants:
    """常量测试"""
    
    def test_intent_types(self):
        """测试意图类型枚举"""
        assert IntentType.NORMAL.value == "normal"
        assert IntentType.FILE.value == "file"
        assert IntentType.WEB.value == "web"
        assert IntentType.SEARCH.value == "search"
    
    def test_message_roles(self):
        """测试消息角色枚举"""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
    
    def test_attachment_types(self):
        """测试附件类型枚举"""
        assert AttachmentType.FILE.value == "file"
        assert AttachmentType.URL.value == "url"
    
    def test_api_paths(self):
        """测试API路径常量"""
        assert APIPaths.PREFIX == "/api"
        assert APIPaths.V1_PREFIX == "/api/v1"
        assert APIPaths.HEALTH == "/api/health"
        assert APIPaths.CHAT == "/api/v1/chat"
        assert APIPaths.UPLOAD == "/api/v1/files/upload"
    
    def test_search_keywords(self):
        """测试搜索关键词"""
        assert "search" in SEARCH_KEYWORDS
        assert "find" in SEARCH_KEYWORDS
        assert "搜索" in SEARCH_KEYWORDS
        assert "查找" in SEARCH_KEYWORDS
        assert len(SEARCH_KEYWORDS) > 10
    
    def test_user_agent(self):
        """测试用户代理字符串"""
        assert "Mozilla" in USER_AGENT
        assert "Chrome" in USER_AGENT
    
    def test_file_config(self):
        """测试文件配置常量"""
        assert FileConfig.MAX_SIZE_MB == 10
        assert FileConfig.MAX_SIZE_BYTES == 10 * 1024 * 1024
        assert ".pdf" in FileConfig.ALLOWED_TYPES
        assert FileConfig.TEMP_DIR == "temp_uploads"
    
    def test_content_limits_constants(self):
        """测试内容限制常量"""
        assert ContentLimits.MAX_CONTENT_LENGTH == 8000
        assert ContentLimits.MAX_WEB_CONTENT_LENGTH == 4000
    
    def test_qwen_config(self):
        """测试通义千问配置常量"""
        assert QwenConfig.DEFAULT_MODEL == "qwen-turbo"
        assert QwenConfig.DEFAULT_TEMPERATURE == 0.7
        assert QwenConfig.DEFAULT_MAX_TOKENS == 3000
        assert QwenConfig.DEFAULT_TOP_P == 0.8
        assert QwenConfig.DEFAULT_REPETITION_PENALTY == 1.1
