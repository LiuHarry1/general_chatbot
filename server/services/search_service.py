"""
搜索服务
负责Tavily搜索功能
"""
import httpx
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

from utils.logger import app_logger
from config import settings


class SearchService:
    """搜索服务"""
    
    def __init__(self):
        self.api_key = settings.tavily_api_key
        self.base_url = "https://api.tavily.com/search"
        self.max_results = settings.tavily_max_results
        self.search_depth = settings.tavily_search_depth
        self.timeout = 30.0
        self.is_configured = bool(self.api_key and self.api_key.strip())
        
        app_logger.info(f"搜索服务初始化 - API密钥: {repr(self.api_key)}, 是否配置: {self.is_configured}")
        
        if not self.is_configured:
            app_logger.warning("Tavily API密钥未配置，搜索功能将使用降级模式")
    
    def validate_query(self, query: str) -> None:
        """验证搜索查询"""
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="搜索查询太短，至少需要2个字符")
        
        if len(query) > 500:
            raise HTTPException(status_code=400, detail="搜索查询太长，最多500个字符")
    
    def format_search_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """格式化搜索结果"""
        formatted_results = {
            "query": results.get("query", ""),
            "answer": results.get("answer", ""),
            "results": [],
            "total_results": len(results.get("results", [])),
            "search_time": results.get("search_time", 0)
        }
        
        # 格式化结果列表
        for result in results.get("results", []):
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
                "published_date": result.get("published_date", "")
            }
            formatted_results["results"].append(formatted_result)
        
        return formatted_results
    
    async def search(self, query: str) -> Dict[str, Any]:
        """执行搜索"""
        try:
            app_logger.info(f"开始Tavily搜索: {query}")
            
            # 验证查询
            self.validate_query(query)
            
            # 检查API密钥配置
            if not self.is_configured:
                raise HTTPException(status_code=503, detail="搜索服务未配置API密钥，请配置TAVILY_API_KEY环境变量")
            
            # 构建请求数据
            request_data = {
                "api_key": self.api_key,
                "query": query.strip(),
                "search_depth": self.search_depth,
                "include_answer": True,
                "include_raw_content": False,
                "max_results": self.max_results,
                "include_domains": [],
                "exclude_domains": []
            }
            
            # 发送搜索请求
            app_logger.info(f"发送搜索请求到: {self.base_url}")
            app_logger.info(f"请求数据: {request_data}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "AI-Chatbot/1.0"
                    }
                )
                app_logger.info(f"搜索响应状态: {response.status_code}")
                app_logger.info(f"搜索响应内容: {response.text[:500]}...")
                response.raise_for_status()
                
                results = response.json()
            
            # 格式化结果
            formatted_results = self.format_search_results(results)
            
            app_logger.info(
                f"搜索完成: {query}, 找到 {formatted_results['total_results']} 个结果, "
                f"耗时: {formatted_results['search_time']}秒"
            )
            
            return formatted_results
            
        except httpx.TimeoutException:
            app_logger.error(f"搜索请求超时: {query}")
            raise HTTPException(status_code=408, detail="搜索请求超时，请稍后重试")
        
        except httpx.HTTPStatusError as e:
            app_logger.error(f"搜索API请求失败: {e.response.status_code}, {e.response.text}")
            if e.response.status_code == 401:
                raise HTTPException(status_code=500, detail="搜索服务认证失败")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="搜索请求过于频繁，请稍后重试")
            else:
                raise HTTPException(status_code=500, detail="搜索服务暂时不可用")
        
        except Exception as e:
            app_logger.error(f"搜索失败: {query}, 错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
    
    async def search_with_fallback(self, query: str) -> Optional[Dict[str, Any]]:
        """带降级的搜索"""
        try:
            return await self.search(query)
        except HTTPException as e:
            app_logger.warning(f"搜索失败，将使用降级模式: {e.detail}")
            return None
        except Exception as e:
            app_logger.warning(f"搜索出现未知错误，将使用降级模式: {e}")
            return None


# 全局搜索服务实例
search_service = SearchService()

