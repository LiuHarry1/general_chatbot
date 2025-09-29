"""
聊天相关API路由
包含聊天对话和流式响应功能
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import ChatRequest, ChatResponse
from services.simple_chat_service import simple_chat_service
from services.ai_service import ai_service
from utils.logger import app_logger

# 创建路由器
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """聊天对话接口"""
    try:
        app_logger.info(f"收到聊天请求 - 对话ID: {chat_request.conversationId}, 消息: {chat_request.message[:100]}...")
        
        # 使用SimpleChatService处理聊天请求
        response = await simple_chat_service.process_chat_request(chat_request)
        
        app_logger.info(f"聊天响应生成完成 - 响应长度: {len(response.content)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail="处理聊天请求时发生错误")


@router.post("/stream")
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
