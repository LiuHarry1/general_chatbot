"""
增强的聊天服务
集成智能意图识别、工具调用和长短期记忆
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

from utils.logger import app_logger
from services.ai_service import ai_service
from services.intent_service import llm_based_intent_service, IntentType
from services.code_execution_service import code_execution_service
from memory import default_memory_manager as memory_manager
from memory.short_term_memory import ShortTermMemoryManager


class EnhancedChatService:
    """增强的聊天服务"""
    
    def __init__(self):
        self.ai_service = ai_service
        self.intent_service = llm_based_intent_service
        self.memory_manager = memory_manager
        self.short_term_memory = ShortTermMemoryManager()
    
    def extract_attachments_data(self, attachments) -> List[Dict[str, Any]]:
        """提取附件数据"""
        attachments_data = []
        if not attachments:
            return attachments_data
            
        for attachment in attachments:
            try:
                # 处理Attachment对象
                if hasattr(attachment, 'data') and hasattr(attachment, 'type'):
                    # 这是Attachment对象
                    if attachment.data and attachment.data.get('content'):
                        attachments_data.append({
                            'filename': attachment.data.get('name', attachment.data.get('filename', 'unknown')),
                            'content': attachment.data['content'],
                            'type': attachment.type
                        })
                elif isinstance(attachment, dict):
                    # 这是字典格式
                    if attachment.get('content'):
                        attachments_data.append({
                            'filename': attachment.get('filename', attachment.get('name', 'unknown')),
                            'content': attachment['content'],
                            'type': attachment.get('type', 'text')
                        })
            except Exception as e:
                app_logger.error(f"处理附件数据失败: {e}")
                continue
                
        return attachments_data
    
    async def extract_user_context(self, message: str, user_id: str) -> Tuple[Dict[str, Any], str, str, List[Dict]]:
        """提取用户上下文信息（集成长短期记忆）"""
        try:
            # 使用长短期记忆系统提取用户偏好和上下文
            user_profile = {}
            contextual_prompt = ""
            short_term_context = ""
            recent_conversations = []
            
            # 从长期记忆获取用户信息
            try:
                user_memories = await self.memory_manager.get_user_memories(user_id)
                if user_memories:
                    contextual_prompt += "\n\n用户历史信息：\n"
                    for memory in user_memories[:5]:  # 取最近5条记忆
                        contextual_prompt += f"- {memory}\n"
            except Exception as e:
                app_logger.error(f"获取长期记忆失败: {e}")
            
            # 从短期记忆获取最近对话上下文
            try:
                recent_conversations = self.short_term_memory.get_recent_conversations(user_id, limit=3)
                if recent_conversations:
                    short_term_context += "\n\n最近对话上下文：\n"
                    for conv in recent_conversations:
                        short_term_context += f"用户: {conv['user_message'][:100]}...\n"
                        short_term_context += f"助手: {conv['ai_response'][:100]}...\n\n"
            except Exception as e:
                app_logger.error(f"获取短期记忆失败: {e}")
            
            return user_profile, contextual_prompt, short_term_context, recent_conversations
            
        except Exception as e:
            app_logger.error(f"提取用户上下文失败: {e}")
            return {}, "", "", []
    
    async def process_query_with_intent(self, message: str, attachments_data: List[Dict[str, Any]], user_id: str) -> Tuple[str, Optional[str], Optional[str], List[str], str]:
        """使用增强意图识别处理查询"""
        # 提取用户上下文（包含最近对话历史）
        user_profile, contextual_prompt, short_term_context, recent_conversations = await self.extract_user_context(message, user_id)
        
        # 使用增强意图识别服务（传入最近对话历史）
        intent_result, _, _, _ = await self.intent_service.process_with_memory(
            message, attachments_data, user_id
        )
        
        # 手动传入最近对话历史到意图识别
        intent_result_with_history = await self.intent_service.process_intent(
            message, attachments_data, user_id, recent_conversations
        )
        
        app_logger.info(f"意图识别结果 - 意图: {intent_result_with_history.intent.value}, 置信度: {intent_result_with_history.confidence}, 推理: {intent_result_with_history.reasoning}")
        
        # 根据意图结果准备参数
        file_content = None
        web_content = None
        search_results = None
        sources = []
        
        if intent_result_with_history.intent == IntentType.FILE:
            file_content = intent_result_with_history.content
        elif intent_result_with_history.intent == IntentType.WEB:
            web_content = intent_result_with_history.content
        elif intent_result_with_history.intent == IntentType.SEARCH:
            search_results = intent_result_with_history.search_results
            # 提取搜索来源
            if search_results and search_results.get("results"):
                sources = [result["url"] for result in search_results["results"]]
        elif intent_result_with_history.intent == IntentType.CODE:
            # 代码执行功能
            pass
        
        return intent_result_with_history.intent.value, file_content, web_content, search_results, sources, intent_result_with_history.reasoning
    
    async def generate_stream_response(self, message: str, intent: str, file_content: Optional[str], 
                                     web_content: Optional[str], search_results: Optional[Dict[str, Any]], 
                                     user_profile: Dict[str, Any], contextual_prompt: str, 
                                     short_term_context: str, user_id: str = "default_user") -> AsyncGenerator[str, None]:
        """生成流式响应"""
        
        if intent == "code":
            # 处理代码执行
            async for chunk in self._handle_code_execution(message, user_profile, contextual_prompt, short_term_context, user_id):
                yield chunk
        else:
            # 处理其他类型的响应
            async for chunk in self.ai_service.generate_stream_response(
                user_message=message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=search_results,
                user_identity=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            ):
                chunk_data = {
                    "type": "content",
                    "content": chunk
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
    
    async def _handle_code_execution(self, message: str, user_profile: Dict[str, Any], 
                                   contextual_prompt: str, short_term_context: str, 
                                   user_id: str) -> AsyncGenerator[str, None]:
        """处理代码执行"""
        try:
            # 首先生成代码
            app_logger.info("开始生成代码")
            
            code_response = ""
            async for chunk in self.ai_service.generate_stream_response(
                user_message=message,
                intent="code",
                file_content=None,
                web_content=None,
                search_results=None,
                user_identity=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            ):
                code_response += chunk
                # 流式发送代码生成过程
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
    
    async def save_conversation_to_memory(self, user_id: str, message: str, response: str, 
                                        intent: str, sources: List[str]):
        """保存对话到长短期记忆"""
        try:
            # 保存到短期记忆
            self.short_term_memory.add_conversation(
                user_id=user_id,
                user_message=message,
                ai_response=response,
                intent=intent,
                sources=sources
            )
            
            # 保存到长期记忆
            await self.memory_manager.add_memory(
                user_id=user_id,
                memory_text=f"用户问: {message[:100]}... 助手回答: {response[:100]}...",
                metadata={"intent": intent, "sources": sources}
            )
            
            app_logger.info(f"对话已保存到长短期记忆: {user_id}")
        except Exception as e:
            app_logger.error(f"保存对话到记忆失败: {e}")
    
    async def process_chat_request(self, chat_request: "ChatRequest") -> "ChatResponse":
        """处理聊天请求"""
        try:
            user_id = getattr(chat_request, 'user_id', 'default_user')
            
            # 提取附件数据
            attachments_data = self.extract_attachments_data(chat_request.attachments)
            
            # 提取用户上下文信息
            user_profile, contextual_prompt, short_term_context, _ = await self.extract_user_context(
                chat_request.message, user_id
            )
            
            # 使用增强意图识别处理查询
            intent, file_content, web_content, search_results, sources, reasoning = await self.process_query_with_intent(
                chat_request.message, attachments_data, user_id
            )
            
            # 生成AI响应
            response_content = await self.ai_service.generate_response(
                user_message=chat_request.message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=search_results,
                user_identity=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context
            )
            
            # 保存对话到长短期记忆
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
            app_logger.error(f"处理聊天请求失败: {e}")
            raise
    
    async def process_stream_request(self, chat_request: "ChatRequest") -> AsyncGenerator[str, None]:
        """处理流式聊天请求"""
        try:
            user_id = getattr(chat_request, 'user_id', 'default_user')
            
            # 提取附件数据
            attachments_data = self.extract_attachments_data(chat_request.attachments)
            
            # 提取用户上下文信息
            user_profile, contextual_prompt, short_term_context, _ = await self.extract_user_context(
                chat_request.message, user_id
            )
            
            # 使用增强意图识别处理查询
            intent, file_content, web_content, search_results, sources, reasoning = await self.process_query_with_intent(
                chat_request.message, attachments_data, user_id
            )
            
            # 收集完整的AI响应
            full_response = ""
            
            # 生成流式响应
            async for chunk in self.generate_stream_response(
                message=chat_request.message,
                intent=intent,
                file_content=file_content,
                web_content=web_content,
                search_results=search_results,
                user_profile=user_profile,
                contextual_prompt=contextual_prompt,
                short_term_context=short_term_context,
                user_id=user_id
            ):
                # 提取chunk内容
                chunk_data = json.loads(chunk.replace("data: ", "").strip())
                if chunk_data.get("type") == "content":
                    full_response += chunk_data.get("content", "")
                yield chunk
            
            # 保存对话到长短期记忆
            await self.save_conversation_to_memory(
                user_id=user_id,
                message=chat_request.message,
                response=full_response,
                intent=intent,
                sources=sources
            )
            
        except Exception as e:
            app_logger.error(f"处理流式聊天请求失败: {e}")
            # 返回错误信息
            error_data = {
                "type": "error",
                "content": f"处理请求时发生错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


# 创建全局实例
enhanced_chat_service = EnhancedChatService()
