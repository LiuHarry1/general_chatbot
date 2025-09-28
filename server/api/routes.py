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
from services.react_agent import react_agent
from services.simple_chat_service import simple_chat_service
from utils.logger import app_logger
from config import settings
from database.api.database_routes import router as database_router


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


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """聊天对话接口"""
    try:
        app_logger.info(f"收到聊天请求 - 对话ID: {chat_request.conversationId}, 消息: {chat_request.message[:100]}...")
        
        # 使用简化版聊天服务处理聊天请求
        response = await simple_chat_service.process_chat_request(chat_request)
        
        app_logger.info(f"聊天响应生成完成 - 响应长度: {len(response.content)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail="处理聊天请求时发生错误")


@router.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest):
    """流式聊天接口"""
    async def generate_stream():
        try:
            app_logger.info(f"收到流式聊天请求: {chat_request.message[:100]}...")
            
            # 处理附件数据
            attachments_data = []
            if chat_request.attachments:
                for att in chat_request.attachments:
                    attachments_data.append({
                        "type": att.type,
                        "data": att.data
                    })
            
            # 提取用户上下文信息
            user_id = getattr(chat_request, 'user_id', 'default_user')
            user_profile, contextual_prompt, short_term_context = await simple_chat_service.extract_user_context(
                chat_request.message, user_id
            )
            
            # 使用React Agent处理查询
            intent, file_content, web_content, sources = await simple_chat_service.process_query_with_react_agent(
                chat_request.message, attachments_data, user_id
            )
            
            # 生成流式AI响应（包含记忆上下文）
            full_response = ""
            async for chunk in ai_service.generate_stream_response(
                user_message=chat_request.message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=None,
                user_identity=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            ):
                chunk_data = {
                    "type": "content",
                    "content": chunk
                }
                full_response += chunk
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            # 保存对话到短期记忆
            await simple_chat_service.save_conversation_to_memory(
                user_id=user_id,
                message=chat_request.message,
                response=full_response,
                intent=intent,
                sources=sources
            )
            
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            app_logger.error(f"流式聊天处理失败: {e}")
            error_data = {
                "type": "error",
                "error": "处理聊天请求时发生错误"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
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
router.include_router(database_router, prefix="/db", tags=["database"])
