"""
pytest配置文件
包含测试固件和配置
"""
import pytest
import asyncio
import sys
from pathlib import Path

# 添加server目录到Python路径
server_path = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_path))

from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_chat_request():
    """示例聊天请求"""
    return {
        "message": "Hello, how are you?",
        "conversationId": "test_conv_123",
        "attachments": [],
        "user_id": "test_user_123"
    }


@pytest.fixture
def sample_file_upload():
    """示例文件上传"""
    return {
        "filename": "test.txt",
        "content": "This is a test file content.",
        "size": 28,
        "type": ".txt"
    }
