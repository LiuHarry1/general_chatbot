"""
API请求和响应模型
用于FastAPI端点的数据验证和序列化
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any


class AttachmentData(BaseModel):
    """附件数据基类"""
    pass


class FileAttachmentData(AttachmentData):
    """文件附件数据"""
    name: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    type: str = Field(..., description="文件类型")
    content: str = Field(..., description="文件内容")


class UrlAttachmentData(AttachmentData):
    """URL附件数据"""
    url: str = Field(..., description="URL地址")
    title: Optional[str] = Field(None, description="网页标题")
    content: str = Field(..., description="网页内容")


class Attachment(BaseModel):
    """附件模型"""
    type: str = Field(..., description="附件类型：file或url")
    data: Dict[str, Any] = Field(..., description="附件数据")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    conversationId: str = Field(..., description="对话ID")
    attachments: Optional[List[Attachment]] = Field(default=[], description="附件列表")
    user_id: Optional[str] = Field(default="default_user", description="用户ID")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str = Field(..., description="AI回复内容")
    intent: str = Field(..., description="意图类型：normal/file/web")
    sources: Optional[List[str]] = Field(default=[], description="搜索来源URL列表")
    timestamp: str = Field(..., description="响应时间戳")


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    content: str = Field(..., description="提取的文本内容")
    filename: str = Field(..., description="原始文件名")
    size: int = Field(..., description="文件大小（字节）")
    type: str = Field(..., description="文件类型")
    extractedLength: int = Field(..., description="提取的文本长度")


class UrlAnalysisRequest(BaseModel):
    """URL分析请求模型"""
    url: str = Field(..., description="要分析的URL")


class UrlAnalysisResponse(BaseModel):
    """URL分析响应模型"""
    title: str = Field(..., description="网页标题")
    content: str = Field(..., description="网页内容")
    url: str = Field(..., description="原始URL")
    analyzedAt: str = Field(..., description="分析时间")
    contentLength: int = Field(..., description="内容长度")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="检查时间")
    uptime: str = Field(..., description="运行时间")


class ServiceStatus(BaseModel):
    """服务状态模型"""
    tongyi: str = Field(..., description="通义千问服务状态")
    tavily: str = Field(..., description="Tavily搜索服务状态")
    fileProcessing: str = Field(..., description="文件处理服务状态")
    webAnalysis: str = Field(..., description="网页分析服务状态")


class StatusResponse(BaseModel):
    """状态响应模型"""
    status: str = Field(..., description="总体状态")
    timestamp: str = Field(..., description="检查时间")
    services: ServiceStatus = Field(..., description="各服务状态")
    version: str = Field(..., description="API版本")


class SupportedFormatsResponse(BaseModel):
    """支持格式响应模型"""
    supportedFormats: List[str] = Field(..., description="支持的文件格式")
    maxFileSize: str = Field(..., description="最大文件大小")
    description: str = Field(..., description="格式说明")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    timestamp: str = Field(..., description="错误时间")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    timestamp: str = Field(..., description="响应时间")
