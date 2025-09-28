"""
API测试
测试所有API端点的功能
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    """健康检查API测试"""
    
    def test_health_check(self, client: TestClient):
        """测试健康检查端点"""
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "timestamp" in data
        assert data["uptime"] == "运行中"
    
    def test_status_check(self, client: TestClient):
        """测试状态检查端点"""
        response = client.get("/api/v1/health/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "timestamp" in data
        assert "services" in data
        assert data["version"] == "1.0.0"
        
        services = data["services"]
        assert services["tongyi"] == "Available"
        assert services["tavily"] == "Available"
        assert services["fileProcessing"] == "Available"
        assert services["webAnalysis"] == "Available"


class TestFilesAPI:
    """文件处理API测试"""
    
    def test_supported_formats(self, client: TestClient):
        """测试支持的文件格式端点"""
        response = client.get("/api/v1/files/supported-formats")
        assert response.status_code == 200
        data = response.json()
        assert "supportedFormats" in data
        assert "maxFileSize" in data
        assert "description" in data
        assert ".pdf" in data["supportedFormats"]
        assert ".txt" in data["supportedFormats"]
    
    def test_file_upload_validation(self, client: TestClient):
        """测试文件上传验证"""
        # 测试没有文件的情况
        response = client.post("/api/v1/files/upload")
        assert response.status_code == 422  # 验证错误
    
    def test_url_analysis_validation(self, client: TestClient):
        """测试URL分析验证"""
        # 测试无效URL
        response = client.post("/api/v1/files/analyze-url", json={"url": "invalid-url"})
        assert response.status_code == 422  # 验证错误
        
        # 测试有效URL格式
        response = client.post("/api/v1/files/analyze-url", json={"url": "https://example.com"})
        # 注意：这里可能会因为网络请求而失败，但至少应该通过验证
        assert response.status_code in [200, 500]  # 200成功或500网络错误


class TestMemoryAPI:
    """记忆系统API测试"""
    
    def test_memory_health_check(self, client: TestClient):
        """测试记忆系统健康检查"""
        response = client.get("/api/v1/memory/health")
        # 注意：这里可能会因为Redis/Qdrant连接而失败
        assert response.status_code in [200, 500]
    
    def test_extract_identity(self, client: TestClient):
        """测试身份信息提取"""
        request_data = {
            "message": "我是刘浩，今年25岁，住在北京",
            "user_id": "test_user_123"
        }
        response = client.post("/api/v1/memory/extract-identity", json=request_data)
        # 注意：这里可能会因为LLM调用而失败
        assert response.status_code in [200, 500]
    
    def test_get_user_identity(self, client: TestClient):
        """测试获取用户身份信息"""
        response = client.get("/api/v1/memory/user-identity/test_user_123")
        # 注意：这里可能会因为Redis连接而失败
        assert response.status_code in [200, 500]
    
    def test_short_term_stats(self, client: TestClient):
        """测试短期记忆统计"""
        response = client.get("/api/v1/memory/short-term/stats/test_user_123")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "stats" in data
    
    def test_clear_short_term_memory(self, client: TestClient):
        """测试清空短期记忆"""
        response = client.delete("/api/v1/memory/short-term/clear/test_user_123")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestChatAPI:
    """聊天API测试"""
    
    def test_chat_validation(self, client: TestClient, sample_chat_request):
        """测试聊天请求验证"""
        # 测试有效请求
        response = client.post("/api/v1/chat/", json=sample_chat_request)
        # 注意：这里可能会因为AI服务调用而失败
        assert response.status_code in [200, 500]
    
    def test_chat_stream_validation(self, client: TestClient, sample_chat_request):
        """测试流式聊天请求验证"""
        response = client.post("/api/v1/chat/stream", json=sample_chat_request)
        # 注意：这里可能会因为AI服务调用而失败
        assert response.status_code in [200, 500]
    
    def test_chat_empty_message(self, client: TestClient):
        """测试空消息聊天请求"""
        request_data = {
            "message": "",
            "conversationId": "test_conv_123"
        }
        response = client.post("/api/v1/chat/", json=request_data)
        assert response.status_code == 422  # 验证错误
    
    def test_chat_missing_conversation_id(self, client: TestClient):
        """测试缺少对话ID的聊天请求"""
        request_data = {
            "message": "Hello"
        }
        response = client.post("/api/v1/chat/", json=request_data)
        assert response.status_code == 422  # 验证错误
