"""
AI服务
负责与通义千问API的交互
"""
import json
import httpx
from typing import List, Dict, Any, Optional
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
    
    def build_system_prompt(self, intent: str, file_content: Optional[str] = None, 
                          web_content: Optional[str] = None, search_results: Optional[Dict] = None) -> str:
        """构建系统提示词"""
        
        base_prompt = "你是一个专业的AI助手，可以帮助用户进行对话、分析文档、搜索网络信息等任务。请用中文回答用户的问题，回答要准确、有用、友好。"
        
        if intent == "file":
            system_prompt = (
                "你是一个专业的文档分析助手。用户上传了文档，请基于文档内容回答用户的问题。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 确保回答基于文档的实际内容\n"
                "3. 如果文档中没有相关信息，请明确说明\n"
                "4. 可以引用文档中的具体内容来支持你的回答\n"
                "5. 保持回答的准确性和客观性"
            )
            if file_content:
                system_prompt += f"\n\n当前分析的文档内容：\n{file_content[:settings.max_content_length]}"
        
        elif intent == "web":
            system_prompt = (
                "你是一个专业的网页内容分析助手。用户提供了网页链接，请基于网页内容回答用户的问题。\n"
                "要求：\n"
                "1. 用中文回答\n"
                "2. 确保回答基于网页的实际内容\n"
                "3. 如果网页中没有相关信息，请明确说明\n"
                "4. 可以引用网页中的具体内容来支持你的回答\n"
                "5. 保持回答的准确性和客观性"
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
                "5. 保持回答的时效性和准确性"
            )
            system_prompt += f"\n\n搜索结果：\n{json.dumps(search_results, ensure_ascii=False, indent=2)}"
        
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
            else:
                raise HTTPException(status_code=500, detail="AI服务暂时不可用")
        
        except Exception as e:
            app_logger.error(f"通义千问API调用失败: {e}")
            raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")
    
    async def generate_response(self, user_message: str, intent: str = "normal", 
                              file_content: Optional[str] = None, 
                              web_content: Optional[str] = None, 
                              search_results: Optional[Dict] = None) -> str:
        """生成AI响应"""
        try:
            app_logger.info(f"开始生成AI响应，意图: {intent}")
            
            # 构建系统提示词
            system_prompt = self.build_system_prompt(intent, file_content, web_content, search_results)
            
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


# 全局AI服务实例
ai_service = AIService()

