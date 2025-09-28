"""
简化的聊天服务
用于调试和测试
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator

from utils.logger import app_logger
from services.react_agent import react_agent
from services.ai_service import ai_service
from memory_simple import default_memory_manager as mem0_manager
from memory_simple.short_term_memory import short_term_memory


class SimpleChatService:
    """简化的聊天服务"""
    
    def __init__(self):
        self.react_agent = react_agent
        self.ai_service = ai_service
        self.mem0_manager = mem0_manager
        self.short_term_memory = short_term_memory
    
    async def process_attachments(self, attachments: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """处理附件数据"""
        if not attachments:
            return []
        
        attachments_data = []
        for att in attachments:
            attachments_data.append({
                "type": att.get("type"),
                "data": att.get("data")
            })
        return attachments_data
    
    async def process_query_with_react_agent(self, message: str, attachments_data: List[Dict[str, Any]], user_id: str) -> Tuple[str, Optional[str], Optional[str], List[str]]:
        """使用React Agent处理查询"""
        # 让React Agent决定如何处理查询
        intent, content, search_results = await self.react_agent.process_query(
            message, 
            attachments_data,
            user_id
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
        
        # 提取搜索来源
        sources = []
        if search_results and search_results.get("results"):
            sources = [result["url"] for result in search_results["results"]]
        
        return intent, file_content, web_content, sources
    
    async def extract_user_context(self, message: str, user_id: str) -> Tuple[Dict[str, Any], str, str]:
        """提取用户上下文信息"""
        try:
            # 使用Mem0提取用户偏好
            preferences = await self.mem0_manager.extract_identity_from_message(
                message, user_id
            )
            
            # 获取用户档案
            user_profile = await self.mem0_manager.get_user_profile(user_id)
            
            # 构建上下文提示词
            contextual_prompt = await self.mem0_manager.build_contextual_prompt(
                user_id, message
            )
            
            # 获取短期记忆上下文
            short_term_context = self.short_term_memory.build_conversation_context(user_id)
            
            # 检查是否需要压缩对话历史
            compressed, compression_summary = await self.short_term_memory.compress_conversations_if_needed(user_id)
            if compressed:
                app_logger.info(f"对话历史已压缩: {user_id}, 摘要: {compression_summary[:100]}...")
            
            return user_profile, contextual_prompt, short_term_context
        except Exception as e:
            app_logger.error(f"提取用户上下文失败: {e}")
            # 如果记忆系统失败，返回空上下文
            return {}, "", ""
    
    async def save_conversation_to_memory(self, user_id: str, message: str, response: str, 
                                        intent: str, sources: List[str]):
        """保存对话到短期记忆"""
        try:
            self.short_term_memory.add_conversation(
                user_id=user_id,
                user_message=message,
                ai_response=response,
                intent=intent,
                sources=sources
            )
            app_logger.info(f"对话已保存到短期记忆: {user_id}")
        except Exception as e:
            app_logger.error(f"保存对话到记忆失败: {e}")

    async def process_chat_request(self, chat_request: "ChatRequest") -> "ChatResponse":
        """处理聊天请求"""
        try:
            app_logger.info(f"开始处理聊天请求: {chat_request.message[:50]}...")
            
            # 处理附件数据
            attachments_data = await self.process_attachments(chat_request.attachments)
            
            # 提取用户上下文信息
            user_id = getattr(chat_request, 'user_id', 'default_user')
            user_profile, contextual_prompt, short_term_context = await self.extract_user_context(
                chat_request.message, user_id
            )
            
            # 使用React Agent处理查询
            intent, file_content, web_content, sources = await self.process_query_with_react_agent(
                chat_request.message, attachments_data, user_id
            )
            
            # 生成AI响应（包含记忆上下文）
            response_content = await self.ai_service.generate_response(
                user_message=chat_request.message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=None,
                user_identity=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            )
            
            app_logger.info(f"AI响应生成完成: {response_content[:50]}...")
            
            # 保存对话到短期记忆
            await self.save_conversation_to_memory(
                user_id=user_id,
                message=chat_request.message,
                response=response_content,
                intent=intent,
                sources=sources
            )
            
            # 返回响应
            from models import ChatResponse
            return ChatResponse(
                content=response_content,
                intent=intent,
                sources=sources,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            app_logger.error(f"聊天请求处理失败: {e}")
            raise


# 创建全局实例
simple_chat_service = SimpleChatService()
