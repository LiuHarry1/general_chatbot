"""
聊天服务
集成智能意图识别、工具调用和模块化记忆系统
"""
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

from utils.logger import app_logger
from services.ai_service import ai_service
from services.intent_service import llm_based_intent_service, IntentType
from services.code_executor import code_execution_service
from memory import unified_memory_manager
from database import conversation_repo
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.schemas import ChatRequest


class ChatService:
    """聊天服务"""
    
    def __init__(self):
        self.ai_service = ai_service
        self.intent_service = llm_based_intent_service
        # 使用新的统一记忆管理器
        self.memory_manager = unified_memory_manager
    
    def extract_attachments_data(self, attachments) -> List[Dict[str, Any]]:
        """提取附件数据"""
        attachments_data = []
        if not attachments:
            return attachments_data
        
        for attachment in attachments:
            try:
                # 根据Attachment模型结构，数据存储在data字段中
                attachment_data = attachment.data if hasattr(attachment, 'data') else attachment
                
                # 构建标准化的附件数据
                processed_attachment = {
                    "type": getattr(attachment, 'type', attachment_data.get('type', 'unknown')),
                    "filename": attachment_data.get('filename', attachment_data.get('name', 'unknown')),
                    "content_type": attachment_data.get('content_type', attachment_data.get('type', 'unknown')),
                    "size": attachment_data.get('size', 0),
                    "content": attachment_data.get('content', ''),
                    "url": attachment_data.get('url', None)
                }
                attachments_data.append(processed_attachment)
            except Exception as e:
                app_logger.error(f"提取附件数据失败: {e}")
        
        return attachments_data
    
    async def extract_user_context(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str
    ) -> Tuple[Dict[str, Any], str, str, List[Dict[str, Any]]]:
        """
        提取用户上下文信息
        返回: (user_profile, contextual_prompt, short_term_context, recent_conversations)
        """
        user_profile = {}
        contextual_prompt = ""
        short_term_context = ""
        recent_conversations = []
        
        try:
            # 使用统一记忆管理器获取完整上下文
            context_result = await self.memory_manager.get_conversation_context(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=message,
                limit=3
            )
            
            # 获取短期记忆上下文
            short_term_context_data = context_result.get("short_term_context", "")
            if short_term_context_data:
                short_term_context = short_term_context_data
            
            # 获取长期记忆上下文
            long_term_context_data = context_result.get("long_term_context", "")
            if long_term_context_data:
                contextual_prompt = long_term_context_data
            
            # 获取用户画像
            user_profile_data = context_result.get("user_profile", {})
            if user_profile_data:
                user_profile = user_profile_data
            
            # 记录上下文信息
            metadata = context_result.get("metadata", {})
            short_term_meta = metadata.get("short_term_metadata", {})
            
            # 获取当前对话的消息历史用于意图识别
            try:
                recent_conversations = conversation_repo.get_current_conversation_messages(
                    conversation_id=conversation_id,
                    limit=5
                )
                app_logger.info(f"获取到当前对话的 {len(recent_conversations)} 条消息用于意图识别")
            except Exception as e:
                app_logger.error(f"获取当前对话消息失败: {e}")
                # 如果获取失败，使用空列表作为fallback
                recent_conversations = []
                    
        except Exception as e:
            app_logger.error(f"获取对话上下文失败: {e}")
        
        return user_profile, contextual_prompt, short_term_context, recent_conversations
    
    async def generate_stream_response(
        self, 
        message: str, 
        intent: str, 
        file_content: Optional[str], 
        web_content: Optional[str], 
        search_results: Optional[List[Dict]], 
        user_identity: Dict[str, Any], 
        contextual_prompt: str, 
        short_term_context: str
    ) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        try:
            async for chunk in self.ai_service.generate_stream_response(
                user_message=message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=search_results,
                user_identity=user_identity,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            ):
                yield chunk
                
        except Exception as e:
            app_logger.error(f"生成流式响应失败: {e}")
            error_data = {
                "type": "content",
                "content": f"❌ 生成响应失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    async def handle_code_execution(
        self, 
        user_id: str, 
        code_response: str
    ) -> AsyncGenerator[str, None]:
        """处理代码执行"""
        try:
            # 发送代码执行提示
            prompt_data = {
                "type": "content",
                "content": "🔧 正在执行代码...\n"
            }
            yield f"data: {json.dumps(prompt_data, ensure_ascii=False)}\n\n"
            
            # 发送代码内容
            for chunk in code_response.split('\n'):
                if chunk.strip():
                    chunk_data = {
                        "type": "content",
                        "content": chunk
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            # 提取代码
            code = self._extract_code_from_response(code_response)
            if not code:
                app_logger.warning("未能从响应中提取到代码")
                return
            
            # 执行代码
            app_logger.info("开始执行代码")
            execution_result = await code_execution_service.execute_code(code, user_id)
            
            # 发送执行结果
            if execution_result["success"]:
                # 发送成功信息
                success_data = {
                    "type": "content",
                    "content": "\n\n✅ 代码执行成功！\n"
                }
                yield f"data: {json.dumps(success_data, ensure_ascii=False)}\n\n"
                
                # 发送输出信息
                if execution_result["output"]:
                    output_data = {
                        "type": "content",
                        "content": f"📋 执行输出：\n```\n{execution_result['output']}\n```\n"
                    }
                    yield f"data: {json.dumps(output_data, ensure_ascii=False)}\n\n"
                
                # 发送图片
                for image_info in execution_result["images"]:
                    image_data = {
                        "type": "image",
                        "url": image_info["url"],
                        "filename": image_info["filename"]
                    }
                    yield f"data: {json.dumps(image_data, ensure_ascii=False)}\n\n"
                    
            else:
                # 发送错误信息
                error_data = {
                    "type": "content",
                    "content": f"\n\n❌ 代码执行失败：\n```\n{execution_result['error']}\n```\n"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            app_logger.error(f"代码执行处理失败: {e}")
            error_data = {
                "type": "content",
                "content": f"\n\n❌ 处理失败：{str(e)}\n"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    def _extract_code_from_response(self, response: str) -> str:
        """从响应中提取Python代码"""
        # 查找代码块
        import re
        
        # 匹配 ```python 或 ``` 代码块
        code_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有找到代码块，尝试查找其他格式
        # 匹配缩进的代码行
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                in_code = True
            elif in_code and (line.startswith('    ') or line.startswith('\t') or line.strip() == ''):
                code_lines.append(line)
            elif in_code and not line.startswith('    ') and not line.startswith('\t') and line.strip():
                break
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return ""
    
    async def save_conversation_to_memory(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str, 
        response: str, 
        intent: str, 
        sources: List[str]
    ):
        """
        保存对话到记忆系统
        使用新的统一记忆管理器处理短期和长期记忆
        """
        try:
            # 使用统一记忆管理器处理对话
            result = await self.memory_manager.process_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                response=response,
                intent=intent,
                sources=sources
            )
            
            # 记录处理结果
            if result.get("success"):
                short_term_result = result.get("short_term", {})
                long_term_result = result.get("long_term", {})
                
                if short_term_result.get("stored"):
                    app_logger.info(f"对话已保存到短期记忆: {user_id}")
                
                if long_term_result.get("stored"):
                    importance = long_term_result.get("importance_score", 0)
                    app_logger.info(f"对话已保存到长期记忆: {user_id}, 重要性: {importance:.2f}")
            else:
                app_logger.warning(f"记忆保存失败: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            app_logger.error(f"保存对话到记忆失败: {e}")
    
    async def process_stream_request(self, request: "ChatRequest") -> AsyncGenerator[str, None]:
        """处理流式聊天请求"""
        try:
            user_id = request.user_id
            conversation_id = request.conversationId
            message = request.message
            attachments = request.attachments or []
            
            app_logger.info(f"处理聊天请求: {user_id}::{conversation_id}")
            
            # 1. 提取附件数据
            attachments_data = self.extract_attachments_data(attachments)
            
            # 2. 提取用户上下文
            user_profile, contextual_prompt, short_term_context, recent_conversations = \
                await self.extract_user_context(user_id, conversation_id, message)
            
            # 3. 意图识别
            intent_result = await self.intent_service.process_intent(
                message=message,
                attachments=attachments_data,
                user_id=user_id,
                recent_conversations=recent_conversations
            )
            intent = intent_result.intent.value
            
            app_logger.info(f"识别意图: {intent}")
            
            # 4. 处理不同意图
            # 准备意图相关的参数
            file_content = None
            web_content = None
            search_results = None
            sources = []
            
            if intent_result.intent == IntentType.FILE:
                file_content = intent_result.content
            elif intent_result.intent == IntentType.WEB:
                web_content = intent_result.content
            elif intent_result.intent == IntentType.SEARCH:
                search_results = intent_result.search_results
                if search_results and search_results.get("results"):
                    sources = [result["url"] for result in search_results["results"]]
            
            if intent == IntentType.CODE:
                # 代码执行流程
                code_response = await self.ai_service.generate_response(
                    user_message=message,
                    intent=intent,
                    file_content=file_content,
                    web_content=web_content,
                    search_results=search_results,
                    user_identity=user_profile,
                    contextual_prompt=contextual_prompt,
                    short_term_context=short_term_context
                )
                
                # 流式发送代码执行结果
                async for chunk in self.handle_code_execution(user_id, code_response):
                    yield chunk
                
                # 保存对话到记忆
                await self.save_conversation_to_memory(
                    user_id, conversation_id, message, code_response, intent, sources
                )
                
            else:
                # 普通对话流程 - 收集完整响应
                full_response = ""
                
                # 转换用户画像数据格式为AI服务期望的格式
                user_identity = {}
                if user_profile and user_profile.get('identity'):
                    identity_data = user_profile.get('identity', {})
                    user_identity = {
                        'name': identity_data.get('name'),
                        'age': identity_data.get('age'),
                        'location': identity_data.get('location'),
                        'job': identity_data.get('job')
                    }
                
                async for chunk in self.generate_stream_response(
                    message=message,
                    intent=intent,
                    file_content=file_content,
                    web_content=web_content,
                    search_results=search_results,
                    user_identity=user_identity,
                    contextual_prompt=contextual_prompt,
                    short_term_context=short_term_context
                ):
                    # 收集完整响应内容
                    full_response += chunk
                    
                    # 格式化chunk为JSON格式
                    chunk_data = {
                        "type": "content",
                        "content": chunk
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                # 保存对话到记忆
                await self.save_conversation_to_memory(
                    user_id, conversation_id, message, full_response, intent, sources
                )
            
        except Exception as e:
            app_logger.error(f"处理聊天请求失败: {e}")
            error_data = {
                "type": "error",
                "content": f"处理请求时发生错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


# 全局实例
chat_service = ChatService()
