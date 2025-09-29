"""
API路由定义
包含所有API端点的实现
"""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from models import (
    ChatRequest, ChatResponse, FileUploadResponse, 
    UrlAnalysisRequest, UrlAnalysisResponse, HealthResponse,
    StatusResponse, SupportedFormatsResponse, ErrorResponse
)
from services.ai_service import ai_service
from services.file_processor import file_processor
from services.web_analyzer import web_analyzer
from services.search_service import search_service
from utils.logger import app_logger
from config import settings


# 创建路由器
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        uptime="运行中"
    )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取服务状态"""
    from models import ServiceStatus
    return StatusResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        services=ServiceStatus(
            tongyi="Available",
            tavily="Available", 
            fileProcessing="Available",
            webAnalysis="Available"
        ),
        version="1.0.0"
    )




@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口"""
    try:
        app_logger.info(f"收到文件上传请求: {file.filename}")
        
        # 处理文件
        result = await file_processor.process_uploaded_file(file)
        
        app_logger.info(f"文件处理完成: {file.filename}, 提取长度: {result['extractedLength']}")
        
        return FileUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文件上传处理失败: {e}")
        raise HTTPException(status_code=500, detail="文件处理失败")


@router.post("/analyze-url", response_model=UrlAnalysisResponse)
async def analyze_url(url_request: UrlAnalysisRequest):
    """网页分析接口"""
    try:
        url = str(url_request.url)
        app_logger.info(f"收到URL分析请求: {url}")
        
        # 分析网页
        result = await web_analyzer.analyze_web_page(url)
        
        app_logger.info(f"URL分析完成: {url}, 内容长度: {result['content_length']}")
        
        return UrlAnalysisResponse(
            title=result["title"],
            content=result["content"],
            url=url,
            analyzedAt=datetime.now().isoformat(),
            contentLength=result["content_length"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"URL分析处理失败: {e}")
        raise HTTPException(status_code=500, detail="网页分析失败")


@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """获取支持的文件格式"""
    return SupportedFormatsResponse(
        supportedFormats=settings.allowed_file_types,
        maxFileSize=f"{settings.max_file_size // 1024 // 1024}MB",
        description="支持的文件格式和大小限制"
    )


# 包含数据库路由
