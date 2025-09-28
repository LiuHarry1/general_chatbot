"""
统一模型定义
导出所有API和数据库模型
"""
from .api_models import (
    ChatRequest,
    ChatResponse,
    FileUploadResponse,
    UrlAnalysisRequest,
    UrlAnalysisResponse,
    HealthResponse,
    StatusResponse,
    ServiceStatus,
    SupportedFormatsResponse,
    ErrorResponse,
    ApiResponse,
    Attachment,
    FileAttachmentData,
    UrlAttachmentData,
    AttachmentData
)

from .db_models import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    MessageUpdate
)

__all__ = [
    # API模型
    'ChatRequest',
    'ChatResponse', 
    'FileUploadResponse',
    'UrlAnalysisRequest',
    'UrlAnalysisResponse',
    'HealthResponse',
    'StatusResponse',
    'ServiceStatus',
    'SupportedFormatsResponse',
    'ErrorResponse',
    'ApiResponse',
    'Attachment',
    'FileAttachmentData',
    'UrlAttachmentData',
    'AttachmentData',
    
    # 数据库模型
    'ConversationCreate',
    'ConversationResponse',
    'MessageCreate',
    'MessageResponse',
    'MessageUpdate'
]
