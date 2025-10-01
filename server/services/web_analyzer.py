"""
网页分析服务
负责网页内容的抓取和分析
"""
import re
from typing import Dict, Any
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from utils.logger import app_logger
from config import settings, USER_AGENT


class WebAnalyzer:
    """网页分析器"""
    
    def __init__(self):
        self.max_content_length = settings.max_web_content_length
        self.timeout = 10.0
    
    def validate_url(self, url: str) -> None:
        """验证URL格式"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("无效的URL格式")
            
            # 检查协议
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("只支持HTTP和HTTPS协议")
                
        except Exception as e:
            app_logger.error(f"URL验证失败: {url}, 错误: {e}")
            raise HTTPException(status_code=400, detail=f"无效的URL格式: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # 限制长度
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length]
            app_logger.warning(f"网页内容过长，已截取前 {self.max_content_length} 个字符")
        
        return text.strip()
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """提取网页标题"""
        title_selectors = [
            'title',
            'h1',
            'meta[property="og:title"]',
            'meta[name="title"]'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    title = element.get('content', '').strip()
                else:
                    title = element.get_text().strip()
                
                if title:
                    return title[:200]  # 限制标题长度
        
        return "无标题"
    
    def extract_content(self, soup: BeautifulSoup) -> str:
        """提取网页主要内容"""
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement']):
            tag.decompose()
        
        # 尝试提取主要内容区域
        content_selectors = [
            'main',
            'article',
            '.content',
            '.main-content',
            '.post-content',
            '.entry-content',
            'body'
        ]
        
        content_text = ""
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                content_text = element.get_text()
                if len(content_text) > 100:  # 确保有足够的内容
                    break
        
        # 如果没有找到合适的内容区域，使用整个body
        if not content_text or len(content_text) < 100:
            body = soup.find('body')
            if body:
                content_text = body.get_text()
            else:
                content_text = soup.get_text()
        
        return self.clean_text(content_text)
    
    async def analyze_web_page(self, url: str) -> Dict[str, Any]:
        """分析网页内容"""
        try:
            app_logger.info(f"开始分析网页: {url}")
            
            # 验证URL
            self.validate_url(url)
            
            # 发送HTTP请求，使用更真实的浏览器Headers
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0',
                    },
                    follow_redirects=True
                )
                response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题和内容
            title = self.extract_title(soup)
            content = self.extract_content(soup)
            
            # 检查是否遇到反爬虫保护
            if len(content) < 100 or "安全验证" in title or "验证" in content[:100]:
                app_logger.warning(f"可能遇到反爬虫保护: {url}, 内容长度: {len(content)}, 标题: {title}")
                raise ValueError(f"无法访问网页内容，可能遇到反爬虫保护。标题：{title}，请尝试其他URL或手动复制内容。")
            
            if not content:
                raise ValueError("无法提取网页内容")
            
            result = {
                "title": title,
                "content": content,
                "url": url,
                "status_code": response.status_code,
                "content_length": len(content)
            }
            
            app_logger.info(f"网页分析完成: {url}, 标题: {title}, 内容长度: {len(content)}")
            return result
            
        except httpx.TimeoutException:
            app_logger.error(f"网页请求超时: {url}")
            raise HTTPException(status_code=408, detail="网页请求超时，请稍后重试")
        
        except httpx.HTTPStatusError as e:
            app_logger.error(f"网页请求失败: {url}, 状态码: {e.response.status_code}")
            raise HTTPException(
                status_code=400, 
                detail=f"无法访问网页，状态码: {e.response.status_code}"
            )
        
        except Exception as e:
            app_logger.error(f"网页分析失败: {url}, 错误: {e}")
            raise HTTPException(status_code=400, detail=f"网页分析失败: {str(e)}")


# 全局网页分析器实例
web_analyzer = WebAnalyzer()

