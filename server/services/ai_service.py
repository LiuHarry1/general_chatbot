"""
AI服务
负责与通义千问API的交互
"""
import json
import httpx
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException

from utils.logger import app_logger
from config import settings


class AIService:
    """AI服务"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = settings.qwen_model
        self.timeout = 60.0
        
        app_logger.info(f"AI服务初始化 - API密钥: {repr(self.api_key[:20])}..., 模型: {self.model}")
    
    def build_system_prompt(self, intent: str, file_content: Optional[str] = None, 
                          web_content: Optional[str] = None, search_results: Optional[Dict] = None,
                          user_identity: Optional[Dict[str, Any]] = None,
                          contextual_prompt: Optional[str] = None,
                          short_term_context: Optional[str] = None) -> str:
        """构建系统提示词"""
        
        base_prompt = "你是一个专业的AI助手，可以帮助用户进行对话、分析文档、搜索网络信息等任务。请用中文回答用户的问题，回答要准确、有用、友好。请确保回答内容积极正面，符合社会价值观。"
        
        # 添加用户身份信息到系统提示词
        if user_identity:
            identity_context = "\n\n用户身份信息："
            if user_identity.get('name'):
                identity_context += f"\n- 姓名：{user_identity['name']}"
            if user_identity.get('age'):
                identity_context += f"\n- 年龄：{user_identity['age']}岁"
            if user_identity.get('location'):
                identity_context += f"\n- 居住地：{user_identity['location']}"
            if user_identity.get('job'):
                identity_context += f"\n- 职业：{user_identity['job']}"
            
            identity_context += "\n\n请记住这些用户信息，在对话中自然地使用这些信息，让用户感受到你认识他们。"
            base_prompt += identity_context
        
        # 添加上下文提示词（Mem0智能记忆）
        if contextual_prompt:
            base_prompt += contextual_prompt
        
        # 添加短期记忆上下文
        if short_term_context:
            base_prompt += short_term_context
        
        if intent == "file":
            system_prompt = (
                "你是一个专业的文档分析助手。用户上传了文档，请基于文档内容回答用户的问题。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 确保回答基于文档的实际内容\n"
                "3. 如果文档中没有相关信息，请明确说明\n"
                "4. 可以引用文档中的具体内容来支持你的回答\n"
                "5. 保持回答的准确性和客观性\n"
                "6. 如果用户上传了多个文档，请综合分析所有文档内容\n"
                "7. 在回答时，可以说明信息来自哪个文档（如果有多个文档）\n"
                "8. 请确保回答内容积极正面，符合社会价值观"
            )
            if file_content:
                # 检查是否包含多个文件的内容（通过分隔符判断）
                if "\n\n" in file_content:
                    system_prompt += f"\n\n当前分析的文档内容（包含多个文件）：\n{file_content[:settings.max_content_length]}"
                else:
                    system_prompt += f"\n\n当前分析的文档内容：\n{file_content[:settings.max_content_length]}"
        
        elif intent == "web":
            system_prompt = (
                "你是一个专业的网页内容分析助手。用户提供了网页链接，请基于网页内容回答用户的问题。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 确保回答基于网页的实际内容\n"
                "3. 如果网页中没有相关信息，请明确说明\n"
                "4. 可以引用网页中的具体内容来支持你的回答\n"
                "5. 保持回答的准确性和客观性\n"
                "6. 请确保回答内容积极正面，符合社会价值观"
            )
            if web_content:
                system_prompt += f"\n\n当前分析的网页内容：\n{web_content[:settings.max_content_length]}"
        
        elif search_results:
            system_prompt = (
                "你是一个专业的搜索助手。用户的问题需要搜索最新信息，请基于搜索结果回答用户的问题。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 基于搜索结果提供准确信息\n"
                "3. 引用相关的信息来源\n"
                "4. 如果搜索结果不够充分，请说明\n"
                "5. 保持回答的时效性和准确性\n"
                "6. 请确保回答内容积极正面，符合社会价值观"
            )
            system_prompt += f"\n\n搜索结果：\n{json.dumps(search_results, ensure_ascii=False, indent=2)}"
        
        elif intent == "code":
            system_prompt = (
                "你是一个专业的Python编程助手，擅长数据分析和可视化。用户的代码将被自动执行并生成图片。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 生成可执行的Python代码\n"
                "3. 如果用户要求画图，使用matplotlib等库生成图表\n"
                "4. 代码要完整、可运行\n"
                "5. 对代码进行必要的注释说明\n"
                "6. 如果涉及数据处理，使用pandas、numpy等库\n"
                "7. 生成的图表要美观、清晰，使用save_plot()函数保存图片\n"
                "8. 请确保代码安全，不执行危险操作\n"
                "9. 请确保回答内容积极正面，符合社会价值观\n\n"
                "重要提示：\n"
                "- 使用save_plot(filename)函数保存图片，不需要plt.show()\n"
                "- 系统会自动执行你的代码并显示生成的图片\n"
                "- 图片将自动保存并显示在聊天界面中"
            )
        
        else:
            system_prompt = base_prompt
        
        return system_prompt
    
    def build_messages(self, user_message: str, system_prompt: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    
    async def call_api(self, messages: List[Dict[str, str]]) -> str:
        """调用通义千问API"""
        try:
            app_logger.info("开始调用通义千问API")
            
            request_data = {
                "model": self.model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "temperature": settings.qwen_temperature,
                    "max_tokens": settings.qwen_max_tokens,
                    "top_p": settings.qwen_top_p,
                    "repetition_penalty": settings.qwen_repetition_penalty
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                
                result = response.json()
            
            # 提取AI响应
            if "output" in result and "text" in result["output"]:
                ai_response = result["output"]["text"]
                app_logger.info(f"通义千问API调用成功，响应长度: {len(ai_response)}")
                return ai_response
            else:
                app_logger.error(f"API响应格式异常: {result}")
                raise HTTPException(status_code=500, detail="AI服务响应格式异常")
        
        except httpx.TimeoutException:
            app_logger.error("通义千问API调用超时")
            raise HTTPException(status_code=408, detail="AI服务响应超时，请稍后重试")
        
        except httpx.HTTPStatusError as e:
            app_logger.error(f"通义千问API请求失败: {e.response.status_code}, {e.response.text}")
            if e.response.status_code == 401:
                raise HTTPException(status_code=500, detail="AI服务认证失败")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="AI服务请求过于频繁，请稍后重试")
            elif e.response.status_code == 400:
                # 检查是否是内容审核失败
                try:
                    error_data = e.response.json()
                    if error_data.get("code") == "DataInspectionFailed":
                        raise HTTPException(status_code=400, detail="内容审核未通过，请尝试使用不同的表达方式")
                except:
                    pass
                raise HTTPException(status_code=400, detail="请求内容不符合规范，请重新表述您的问题")
            else:
                raise HTTPException(status_code=500, detail="AI服务暂时不可用")
        
        except Exception as e:
            app_logger.error(f"通义千问API调用失败: {e}")
            raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")
    
    async def generate_response(self, user_message: str, intent: str = "normal", 
                              file_content: Optional[str] = None, 
                              web_content: Optional[str] = None, 
                              search_results: Optional[Dict] = None,
                              user_identity: Optional[Dict[str, Any]] = None,
                              contextual_prompt: Optional[str] = None,
                              short_term_context: Optional[str] = None) -> str:
        """生成AI响应"""
        try:
            app_logger.info(f"开始生成AI响应，意图: {intent}")
            
            # 构建系统提示词
            system_prompt = self.build_system_prompt(intent, file_content, web_content, search_results, user_identity, contextual_prompt, short_term_context)
            
            # 构建消息列表
            messages = self.build_messages(user_message, system_prompt)
            
            # 调用API
            response = await self.call_api(messages)
            
            app_logger.info(f"AI响应生成完成，意图: {intent}, 响应长度: {len(response)}")
            return response
        
        except HTTPException:
            raise
        except Exception as e:
            app_logger.error(f"AI响应生成失败: {e}")
            raise HTTPException(status_code=500, detail=f"AI响应生成失败: {str(e)}")
    
    async def generate_stream_response(
        self,
        user_message: str,
        intent: str = "chat",
        file_content: Optional[str] = None,
        web_content: Optional[str] = None,
        search_results: Optional[Dict[str, Any]] = None,
        user_identity: Optional[Dict[str, Any]] = None,
        contextual_prompt: Optional[str] = None,
        short_term_context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """生成流式AI响应"""
        try:
            app_logger.info(f"开始生成流式AI响应，意图: {intent}")
            
            # 构建系统提示词
            system_prompt = self.build_system_prompt(intent, file_content, web_content, search_results, user_identity, contextual_prompt, short_term_context)
            
            # 构建消息列表
            messages = self.build_messages(user_message, system_prompt)
            
            # 获取完整响应
            full_response = await self.call_api(messages)
            
            # 将响应分块发送，模拟流式效果
            chunk_size = 3  # 每次发送3个字符
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i + chunk_size]
                yield chunk
                # 添加小延迟模拟真实流式效果
                await asyncio.sleep(0.05)
            
            app_logger.info(f"流式AI响应生成完成，意图: {intent}, 响应长度: {len(full_response)}")
        
        except Exception as e:
            app_logger.error(f"流式AI响应生成失败: {e}")
            yield f"错误: {str(e)}"


# 全局AI服务实例
ai_service = AIService()

