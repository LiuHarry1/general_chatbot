"""
统一大语言模型调用客户端
集中管理所有与通义千问文本生成API的交互，提高代码可维护性
"""
import json
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from utils.logger import app_logger
from config import settings

logger = logging.getLogger(__name__)


class QwenClient:
    """
    通义千问文本生成统一客户端
    负责所有大语言模型API调用
    """
    
    def __init__(self):
        # API配置
        self.api_key = settings.dashscope_api_key
        self.base_url = settings.qwen_api_url
        self.model = settings.qwen_model
        self.timeout = settings.qwen_timeout
        
        # 文本生成默认参数
        self.default_params = {
            "temperature": settings.qwen_temperature,
            "max_tokens": settings.qwen_max_tokens,
            "top_p": settings.qwen_top_p,
            "repetition_penalty": settings.qwen_repetition_penalty
        }
        
        app_logger.info(f"QwenClient initialized - Model: {self.model}, API: {self.base_url}, Timeout: {self.timeout}s, Stream: SSE")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一的API请求方法
        
        Args:
            payload: 请求payload
            
        Returns:
            API响应数据
            
        Raises:
            TimeoutError: 请求超时
            PermissionError: 认证失败
            ValueError: 请求参数错误或内容审核失败
            Exception: 其他错误
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("Qwen API timeout")
            raise TimeoutError("大语言模型API调用超时，请稍后重试")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Qwen API error: {e.response.status_code}, {e.response.text}")
            self._handle_http_error(e)
        
        except Exception as e:
            logger.error(f"Qwen API call failed: {e}")
            raise Exception(f"大语言模型API调用失败: {str(e)}")
    
    def _handle_http_error(self, error: httpx.HTTPStatusError):
        """处理HTTP错误"""
        status_code = error.response.status_code
        
        if status_code == 401:
            raise PermissionError("API认证失败，请检查API密钥")
        elif status_code == 429:
            raise Exception("API请求过于频繁，请稍后重试")
        elif status_code == 400:
            # 检查是否是内容审核失败
            try:
                error_data = error.response.json()
                if error_data.get("code") == "DataInspectionFailed":
                    raise ValueError("内容审核未通过，请尝试使用不同的表达方式")
            except:
                pass
            raise ValueError("请求内容不符合规范，请重新表述您的问题")
        else:
            raise Exception("大语言模型服务暂时不可用")
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        repetition_penalty: Optional[float] = None
    ) -> str:
        """
        生成文本（对话）
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数（0.0-2.0），覆盖默认值。值越高输出越随机
            max_tokens: 最大token数，覆盖默认值
            top_p: Top-P参数（0.0-1.0），覆盖默认值
            repetition_penalty: 重复惩罚系数（1.0-2.0），覆盖默认值
            
        Returns:
            生成的文本
            
        Raises:
            TimeoutError: 请求超时
            PermissionError: 认证失败
            ValueError: 参数错误或内容审核失败
            Exception: 其他错误
        """
        # 构建参数
        params = self.default_params.copy()
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if top_p is not None:
            params["top_p"] = top_p
        if repetition_penalty is not None:
            params["repetition_penalty"] = repetition_penalty
        
        # 构建请求payload
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": params
        }
        
        # 调用API
        result = await self._make_request(payload)
        
        # 提取响应文本
        if "output" in result and "text" in result["output"]:
            text = result["output"]["text"]
            app_logger.info(f"✅ [LLM] Text generation successful, length: {len(text)}")
            return text
        else:
            logger.error(f"Unexpected API response format: {result}")
            raise ValueError("API响应格式异常")
    
    async def generate_text_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式生成文本（真正的SSE流式输出）
        
        通义千问原生支持Server-Sent Events (SSE)流式输出
        
        Args:
            messages: 对话消息列表
            **kwargs: 传递给API的其他参数（temperature, max_tokens等）
            
        Yields:
            文本片段
        """
        # 构建参数
        params = self.default_params.copy()
        for key in ['temperature', 'max_tokens', 'top_p', 'repetition_penalty']:
            if key in kwargs:
                params[key] = kwargs[key]
        
        # 构建请求payload，启用流式输出
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                **params,
                "incremental_output": True  # 启用增量输出（流式）
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    json=payload,
                    headers={
                        **self._get_headers(),
                        "Accept": "text/event-stream",  # SSE格式
                        "X-DashScope-SSE": "enable"     # 启用SSE
                    }
                ) as response:
                    response.raise_for_status()
                    
                    # 处理SSE流
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            # 跳过空行和注释行
                            continue
                        
                        if line.startswith("data:"):
                            # 提取数据部分
                            data_str = line[5:].strip()
                            
                            # 跳过结束标记
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                # 解析JSON数据
                                data = json.loads(data_str) if data_str else {}
                                
                                # 提取文本片段
                                if "output" in data and "text" in data["output"]:
                                    chunk = data["output"]["text"]
                                    if chunk:
                                        yield chunk
                                        
                            except json.JSONDecodeError:
                                # 忽略无法解析的数据
                                continue
                    
                    app_logger.info("✅ [LLM-STREAM] Stream generation completed")
                    
        except httpx.TimeoutException:
            logger.error("Qwen streaming API timeout")
            yield "错误: API调用超时"
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Qwen streaming API error: {e.response.status_code}")
            yield f"错误: API请求失败"
        
        except Exception as e:
            logger.error(f"Qwen streaming API call failed: {e}")
            yield f"错误: {str(e)}"



# 全局客户端实例
qwen_client = QwenClient()
