"""
聊天相关API路由
包含聊天对话和流式响应功能
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import ChatRequest
from services.chat_service import chat_service
from utils.logger import app_logger

# 创建路由器
router = APIRouter()


@router.post("/stream")
async def chat_stream(chat_request: ChatRequest):
    """流式聊天接口"""
    async def generate_stream():
        try:
            app_logger.info(f"收到流式聊天请求: {chat_request.message[:100]}...")
            
            # 使用ChatService处理流式聊天请求
            async for chunk in chat_service.process_stream_request(chat_request):
                yield chunk
                
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
