"""
API路由定义
包含所有API端点的实现
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse

from models import (
    ChatRequest, ChatResponse, FileUploadResponse, 
    UrlAnalysisRequest, UrlAnalysisResponse, HealthResponse,
    StatusResponse, SupportedFormatsResponse, ErrorResponse
)
from services.ai_service import ai_service
from services.file_processor import file_processor
from services.web_analyzer import web_analyzer
from services.search_service import search_service
from services.react_agent import react_agent
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
    return StatusResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        services={
            "tongyi": "Available",
            "tavily": "Available", 
            "fileProcessing": "Available",
            "webAnalysis": "Available"
        },
        version="1.0.0"
    )


@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """获取支持的文件格式"""
    return SupportedFormatsResponse(
        supportedFormats=settings.allowed_file_types,
        maxFileSize=f"{settings.max_file_size // 1024 // 1024}MB",
        description="支持的文件格式和大小限制"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """聊天对话接口"""
    try:
        app_logger.info(f"收到聊天请求 - 对话ID: {chat_request.conversationId}, 消息: {chat_request.message[:100]}...")
        
        # 使用React Agent处理查询
        attachments_data = []
        if chat_request.attachments:
            for att in chat_request.attachments:
                attachments_data.append({
                    "type": att.type,
                    "data": att.data
                })
        
        # 让React Agent决定如何处理查询
        intent, content, search_results = await react_agent.process_query(
            chat_request.message, 
            attachments_data
        )
        
        app_logger.info(f"React Agent处理结果 - 意图: {intent}")
        
        # 根据Agent的决定准备参数
        file_content = None
        web_content = None
        
        if intent == "file":
            file_content = content
        elif intent == "web":
            web_content = content
        elif intent == "search":
            # 搜索意图，使用原始消息
            pass
        
        # 生成AI响应
        ai_response = await ai_service.generate_response(
            user_message=chat_request.message,
            intent=intent,
            file_content=file_content,
            web_content=web_content,
            search_results=search_results
        )
        
        # 提取搜索来源
        sources = []
        if search_results and search_results.get("results"):
            sources = [result["url"] for result in search_results["results"]]
        
        app_logger.info(f"聊天响应生成完成 - 意图: {intent}, 响应长度: {len(ai_response)}")
        
        return ChatResponse(
            content=ai_response,
            intent=intent,
            sources=sources,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail="处理聊天请求时发生错误")


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


# 错误处理已移至main.py中的全局异常处理器

