"""
聊天服务
集成智能意图识别、工具调用和模块化记忆系统
"""
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

from utils.logger import app_logger, log_execution_time
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
    
    @log_execution_time(log_args=True)
    async def extract_user_context(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        提取用户上下文信息
        返回: (full_context, recent_conversations)
        """
        try:
            # 使用统一记忆管理器获取完整上下文
            context_result = await self.memory_manager.get_conversation_context(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=message,
                limit=3
            )
            
            # 提取完整上下文
            full_context = context_result.get("full_context", "")
            
            # 从短期记忆的 metadata 中提取对话历史
            recent_conversations = []
            metadata = context_result.get("metadata", {})
            short_term_metadata = metadata.get("short_term_metadata", {})
            if short_term_metadata:
                recent_conversations = short_term_metadata.get("conversations", [])
                app_logger.info(f"✅ 从短期记忆中提取到 {len(recent_conversations)} 条对话")
            
            return full_context, recent_conversations
                    
        except Exception as e:
            app_logger.error(f"获取对话上下文失败: {e}")
            # 返回空值
            return "", []
    
    async def generate_stream_response(
        self, 
        message: str, 
        intent: str, 
        file_content: Optional[str], 
        web_content: Optional[str], 
        search_results: Optional[List[Dict]], 
        full_context: str
    ) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        try:
            async for chunk in self.ai_service.generate_stream_response(
                user_message=message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=search_results,
                full_context=full_context
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
            
            app_logger.info(f"📝 提取到的代码:\n{code[:200]}...")
            
            # 执行代码
            app_logger.info("🚀 开始执行代码")
            execution_result = await code_execution_service.execute_code(code, user_id)
            
            app_logger.info(f"✅ 执行完成: success={execution_result['success']}, images={len(execution_result['images'])}")
            
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
                app_logger.info(f"📸 准备发送 {len(execution_result['images'])} 张图片")
                for i, image_info in enumerate(execution_result["images"]):
                    app_logger.info(f"📸 图片 {i+1}: {image_info['url']}")
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
    
    async def create_messages_after_stream(
        self, 
        user_id: str, 
        conversation_id: str, 
        user_message: str, 
        ai_response: str, 
        intent: str, 
        sources: List[str], 
        attachments_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        在流式响应完成后创建用户消息和AI消息
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            user_message: 用户消息内容
            ai_response: AI响应内容
            intent: 意图类型
            sources: 来源列表
            attachments_data: 附件数据
            
        Returns:
            Dict: 消息创建结果，包含成功或错误信息
        """
        try:
            from database.repositories.message_repository import MessageRepository
            from database.connection import DatabaseManager
            
            # 初始化数据库管理器
            db_manager = DatabaseManager()
            message_repo = MessageRepository(db_manager)
            
            # 创建用户消息
            user_message_id = self._create_user_message(
                message_repo, conversation_id, user_message, attachments_data
            )
            
            # 创建AI消息
            ai_message_id = self._create_ai_message(
                message_repo, conversation_id, ai_response, intent, sources
            )
            
            # 构建成功响应
            return {
                "type": "message_created",
                "user_message_id": user_message_id,
                "ai_message_id": ai_message_id,
                "conversation_id": conversation_id,
                "intent": intent,
                "sources": sources
            }
            
        except Exception as e:
            app_logger.error(f"创建消息失败: {e}")
            return {
                "type": "message_creation_error",
                "error": f"创建消息失败: {str(e)}"
            }
    
    def _create_user_message(
        self, 
        message_repo, 
        conversation_id: str, 
        user_message: str, 
        attachments_data: List[Dict[str, Any]]
    ) -> str:
        """创建用户消息"""
        user_message_id = message_repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            intent=None,
            sources=None,
            attachments=attachments_data,
            is_typing=False
        )
        app_logger.info(f"创建用户消息成功: {user_message_id}")
        return user_message_id
    
    def _create_ai_message(
        self, 
        message_repo, 
        conversation_id: str, 
        ai_response: str, 
        intent: str, 
        sources: List[str]
    ) -> str:
        """创建AI消息"""
        ai_message_id = message_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response,
            intent=intent,
            sources=sources,
            attachments=None,
            is_typing=False
        )
        app_logger.info(f"创建AI消息成功: {ai_message_id}")
        return ai_message_id
    
    async def process_stream_request(self, request: "ChatRequest") -> AsyncGenerator[str, None]:
        """
        处理流式聊天请求
        
        Args:
            request: 聊天请求对象
            
        Yields:
            str: 流式响应数据
        """
        try:
            # 解析请求参数
            user_id, conversation_id, message, attachments = self._parse_request(request)
            app_logger.info(f"💬 [{user_id}] {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # 预处理请求
            attachments_data = self.extract_attachments_data(attachments)
            full_context, recent_conversations = await self.extract_user_context(
                user_id, conversation_id, message
            )
            
            # 意图识别和处理
            intent_result = await self.intent_service.process_intent(
                message=message,
                attachments=attachments_data,
                user_id=user_id,
                recent_conversations=recent_conversations
            )
            intent = intent_result.intent.value
            app_logger.info(f"🎯 Intent: {intent} | Reason: {intent_result.reasoning}")
            
            # 准备意图相关参数
            intent_params = self._prepare_intent_parameters(intent_result)
            
            # 根据意图类型处理请求
            if intent == "code":
                app_logger.info("🔧 处理代码执行意图")
                async for chunk in self._handle_code_intent(
                    user_id, conversation_id, message, intent, intent_params, 
                    full_context, attachments_data
                ):
                    yield chunk
            else:
                app_logger.info(f"💬 处理普通对话意图: {intent}")
                async for chunk in self._handle_normal_intent(
                    user_id, conversation_id, message, intent, intent_params,
                    full_context, attachments_data
                ):
                    yield chunk
            
        except Exception as e:
            app_logger.error(f"处理聊天请求失败: {e}")
            error_data = {
                "type": "error",
                "content": f"处理请求时发生错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    def _parse_request(self, request: "ChatRequest") -> Tuple[str, str, str, List]:
        """解析请求参数"""
        return (
            request.user_id,
            request.conversationId,
            request.message,
            request.attachments or []
        )
    
    def _prepare_intent_parameters(self, intent_result) -> Dict[str, Any]:
        """准备意图相关参数"""
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
        
        return {
            "file_content": file_content,
            "web_content": web_content,
            "search_results": search_results,
            "sources": sources
        }
    
    async def _handle_code_intent(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str, 
        intent: str, 
        intent_params: Dict[str, Any],
        full_context: str, 
        attachments_data: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        处理代码执行意图 - 两阶段处理
        
        阶段1：生成并执行代码（工具调用）
        阶段2：基于执行结果回答用户问题
        """
        
        # === 阶段1：生成并执行代码（作为工具使用）===
        app_logger.info("🔧 [阶段1] 生成代码")
        
        # 发送处理提示
        processing_data = {
            "type": "content",
            "content": "🔍 正在处理您的请求...\n\n"
        }
        yield f"data: {json.dumps(processing_data, ensure_ascii=False)}\n\n"
        
        # 生成代码
        code_response = await self.ai_service.generate_response(
            user_message=message,
            intent=intent,
            file_content=intent_params["file_content"],
            web_content=intent_params["web_content"],
            search_results=intent_params["search_results"],
            full_context=full_context
        )
        
        # 提取代码
        code = self._extract_code_from_response(code_response)
        if not code:
            app_logger.warning("未能提取代码")
            error_data = {"type": "content", "content": "❌ 无法生成分析代码\n"}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            return
        
        app_logger.info(f"📝 代码:\n{code[:200]}...")
        
        # 执行代码
        app_logger.info("🚀 [阶段1] 执行代码")
        execution_result = await code_execution_service.execute_code(code, user_id)
        
        if not execution_result["success"]:
            app_logger.error(f"执行失败: {execution_result['error']}")
            error_data = {"type": "content", "content": f"❌ 执行失败: {execution_result['error']}\n"}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            return
        
        app_logger.info(f"✅ [阶段1] 执行成功 - 输出: {len(execution_result['output'])}字符, 图片: {len(execution_result['images'])}张")
        
        # === 阶段2：基于执行结果回答用户问题 ===
        app_logger.info("💬 [阶段2] 基于执行结果生成回答")
        
        # 构建包含执行结果的提示词
        result_context = f"""
用户问题：{message}

代码执行结果：
"""
        if execution_result["output"]:
            result_context += f"- 输出数据：\n{execution_result['output']}\n"
        
        if execution_result["images"]:
            result_context += f"- 生成了 {len(execution_result['images'])} 张图表\n"
        
        result_context += """
请基于以上执行结果，直接回答用户的问题。
要求：
1. 用自然语言回答，不要显示代码
2. 如果有数据输出，解释数据的含义
3. 如果生成了图表，简要说明图表展示的内容
4. 回答要简洁、专业、准确
"""
        
        # 流式生成最终回答
        final_response = ""
        async for chunk in self.ai_service.generate_stream_response(
            user_message=result_context,
            intent="normal",
            full_context=full_context
        ):
            final_response += chunk
            chunk_data = {"type": "content", "content": chunk}
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        # 发送图片（如果有）
        for image_info in execution_result["images"]:
            app_logger.info(f"📸 发送图片: {image_info['filename']}")
            image_data = {
                "type": "image",
                "url": image_info["url"],
                "filename": image_info["filename"]
            }
            yield f"data: {json.dumps(image_data, ensure_ascii=False)}\n\n"
            
            # 将图片 markdown 添加到响应中（用于数据库保存）
            full_image_url = f"http://localhost:3001{image_info['url']}" if not image_info['url'].startswith('http') else image_info['url']
            final_response += f"\n\n![{image_info['filename']}]({full_image_url})"
        
        app_logger.info(f"📝 [阶段2] 最终响应: {len(final_response)}字符")
        
        # 保存到数据库
        async for chunk in self._finalize_stream_response(
            user_id, conversation_id, message, final_response, intent, 
            intent_params["sources"], attachments_data
        ):
            yield chunk
    
    async def _handle_normal_intent(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str, 
        intent: str, 
        intent_params: Dict[str, Any],
        full_context: str, 
        attachments_data: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """处理普通对话意图"""
        # 流式生成响应
        full_response = ""
        async for chunk in self.generate_stream_response(
            message=message,
            intent=intent,
            file_content=intent_params["file_content"],
            web_content=intent_params["web_content"],
            search_results=intent_params["search_results"],
            full_context=full_context
        ):
            full_response += chunk
            chunk_data = {
                "type": "content",
                "content": chunk
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        # 完成流式响应后的处理
        async for chunk in self._finalize_stream_response(
            user_id, conversation_id, message, full_response, intent, 
            intent_params["sources"], attachments_data
        ):
            yield chunk
    
    async def _finalize_stream_response(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str, 
        response: str, 
        intent: str, 
        sources: List[str], 
        attachments_data: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """完成流式响应后的处理"""
        # 创建消息
        message_created_data = await self.create_messages_after_stream(
            user_id, conversation_id, message, response, intent, sources, attachments_data
        )
        
        # 发送消息创建完成的信号
        yield f"data: {json.dumps(message_created_data, ensure_ascii=False)}\n\n"
        
        # 发送结束信号
        yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
        
        # 保存对话到记忆
        await self.save_conversation_to_memory(
            user_id, conversation_id, message, response, intent, sources
        )


# 全局实例
chat_service = ChatService()
