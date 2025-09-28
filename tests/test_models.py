"""
模型测试
测试所有数据模型的创建和验证
"""
import pytest
from datetime import datetime

from server.models import (
    ChatRequest, ChatResponse, FileUploadResponse,
    UrlAnalysisRequest, UrlAnalysisResponse, HealthResponse,
    StatusResponse, SupportedFormatsResponse, ErrorResponse,
    Attachment, FileAttachmentData, UrlAttachmentData,
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse, MessageUpdate
)


class TestAPIModels:
    """API模型测试"""
    
    def test_chat_request_creation(self):
        """测试ChatRequest模型创建"""
        request = ChatRequest(
            message="Hello, world!",
            conversationId="conv_123"
        )
        assert request.message == "Hello, world!"
        assert request.conversationId == "conv_123"
        assert request.attachments == []
        assert request.user_id == "default_user"
    
    def test_chat_request_validation(self):
        """测试ChatRequest模型验证"""
        # 测试空消息
        with pytest.raises(ValueError):
            ChatRequest(message="", conversationId="conv_123")
        
        # 测试消息过长
        long_message = "x" * 4001
        with pytest.raises(ValueError):
            ChatRequest(message=long_message, conversationId="conv_123")
    
    def test_chat_response_creation(self):
        """测试ChatResponse模型创建"""
        response = ChatResponse(
            content="Hello! How can I help you?",
            intent="normal",
            timestamp=datetime.now().isoformat()
        )
        assert response.content == "Hello! How can I help you?"
        assert response.intent == "normal"
        assert response.sources == []
    
    def test_file_attachment_data(self):
        """测试文件附件数据模型"""
        attachment_data = FileAttachmentData(
            name="test.txt",
            size=1024,
            type=".txt",
            content="Test content"
        )
        assert attachment_data.name == "test.txt"
        assert attachment_data.size == 1024
        assert attachment_data.type == ".txt"
        assert attachment_data.content == "Test content"
    
    def test_url_attachment_data(self):
        """测试URL附件数据模型"""
        attachment_data = UrlAttachmentData(
            url="https://example.com",
            title="Example Site",
            content="Example content"
        )
        assert attachment_data.url == "https://example.com"
        assert attachment_data.title == "Example Site"
        assert attachment_data.content == "Example content"
    
    def test_attachment_model(self):
        """测试附件模型"""
        file_data = FileAttachmentData(
            name="test.txt",
            size=1024,
            type=".txt",
            content="Test content"
        )
        
        attachment = Attachment(
            type="file",
            data=file_data.dict()
        )
        assert attachment.type == "file"
        assert attachment.data["name"] == "test.txt"
    
    def test_health_response(self):
        """测试健康检查响应模型"""
        response = HealthResponse(
            status="OK",
            timestamp=datetime.now().isoformat(),
            uptime="运行中"
        )
        assert response.status == "OK"
        assert response.uptime == "运行中"


class TestDatabaseModels:
    """数据库模型测试"""
    
    def test_conversation_create(self):
        """测试ConversationCreate模型"""
        conversation = ConversationCreate(
            title="Test Conversation",
            user_id="user_123"
        )
        assert conversation.title == "Test Conversation"
        assert conversation.user_id == "user_123"
    
    def test_conversation_response(self):
        """测试ConversationResponse模型"""
        response = ConversationResponse(
            id="conv_123",
            title="Test Conversation",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        assert response.id == "conv_123"
        assert response.title == "Test Conversation"
    
    def test_message_create(self):
        """测试MessageCreate模型"""
        message = MessageCreate(
            conversation_id="conv_123",
            role="user",
            content="Hello!",
            intent="normal"
        )
        assert message.conversation_id == "conv_123"
        assert message.role == "user"
        assert message.content == "Hello!"
        assert message.intent == "normal"
        assert message.is_typing == False
    
    def test_message_response(self):
        """测试MessageResponse模型"""
        response = MessageResponse(
            id="msg_123",
            conversation_id="conv_123",
            role="user",
            content="Hello!",
            created_at=datetime.now().isoformat()
        )
        assert response.id == "msg_123"
        assert response.conversation_id == "conv_123"
        assert response.role == "user"
        assert response.content == "Hello!"
    
    def test_message_update(self):
        """测试MessageUpdate模型"""
        update = MessageUpdate(
            content="Updated content",
            intent="file"
        )
        assert update.content == "Updated content"
        assert update.intent == "file"
        assert update.sources is None
        assert update.is_typing is None
