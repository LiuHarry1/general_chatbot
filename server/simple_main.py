"""
简化版Python后端
使用标准库实现，不依赖外部包
"""
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import base64
from datetime import datetime


class ChatbotAPIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""
    
    def __init__(self, *args, **kwargs):
        # API配置
        self.dashscope_api_key = "sk-f256c03643e9491fb1ebc278dd958c2d"
        self.tavily_api_key = "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"
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/health':
            self.handle_health()
        elif self.path == '/api/status':
            self.handle_status()
        elif self.path == '/api/supported-formats':
            self.handle_supported_formats()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/chat':
            self.handle_chat()
        elif self.path == '/api/upload':
            self.handle_upload()
        elif self.path == '/api/analyze-url':
            self.handle_analyze_url()
        else:
            self.send_error(404, "Not Found")
    
    def send_json_response(self, data, status_code=200):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def handle_health(self):
        """健康检查"""
        self.send_json_response({
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "uptime": "运行中"
        })
    
    def handle_status(self):
        """服务状态"""
        self.send_json_response({
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "tongyi": "Available",
                "tavily": "Available",
                "fileProcessing": "Available",
                "webAnalysis": "Available"
            },
            "version": "1.0.0"
        })
    
    def handle_supported_formats(self):
        """支持的文件格式"""
        self.send_json_response({
            "supportedFormats": [".pdf", ".txt", ".doc", ".docx", ".md"],
            "maxFileSize": "10MB",
            "description": "支持的文件格式和大小限制"
        })
    
    def handle_chat(self):
        """聊天处理"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            message = data.get('message', '')
            attachments = data.get('attachments', [])
            
            # 确定意图
            intent = "normal"
            file_content = None
            web_content = None
            
            if attachments:
                file_attachment = next((att for att in attachments if att.get('type') == 'file'), None)
                url_attachment = next((att for att in attachments if att.get('type') == 'url'), None)
                
                if file_attachment:
                    intent = "file"
                    file_content = file_attachment.get('data', {}).get('content', '')
                
                if url_attachment:
                    intent = "web"
                    web_content = url_attachment.get('data', {}).get('content', '')
            
            # 检查是否需要搜索
            search_keywords = ['search', 'find', 'look up', 'what is', 'how to', 'where is', 
                             '搜索', '查找', '寻找', '什么是', '如何', '哪里', '最新', '新闻', '资讯']
            needs_search = any(keyword.lower() in message.lower() for keyword in search_keywords) and intent == "normal"
            
            search_results = None
            if needs_search:
                search_results = self.search_with_tavily(message)
            
            # 调用通义千问
            ai_response = self.call_tongyi_qwen(message, intent, file_content, web_content, search_results)
            
            # 提取搜索来源
            sources = []
            if search_results and search_results.get('results'):
                sources = [result['url'] for result in search_results['results']]
            
            self.send_json_response({
                "content": ai_response,
                "intent": intent,
                "sources": sources,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.send_json_response({
                "error": "处理聊天请求时发生错误",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500)
    
    def handle_upload(self):
        """文件上传处理"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # 解析multipart数据
            boundary = self.headers.get('Content-Type', '').split('boundary=')[-1]
            if not boundary:
                self.send_json_response({
                    "error": "无效的文件格式",
                    "timestamp": datetime.now().isoformat()
                }, 400)
                return
            
            # 简单的multipart解析
            parts = post_data.split(f'--{boundary}'.encode())
            file_data = None
            filename = "unknown"
            file_type = ".txt"
            
            for part in parts:
                if b'Content-Disposition: form-data' in part and b'filename=' in part:
                    # 提取文件名
                    filename_match = re.search(rb'filename="([^"]+)"', part)
                    if filename_match:
                        filename = filename_match.group(1).decode('utf-8', errors='ignore')
                        file_type = os.path.splitext(filename)[1].lower()
                    
                    # 提取文件内容
                    content_start = part.find(b'\r\n\r\n')
                    if content_start != -1:
                        file_data = part[content_start + 4:-2]  # 去掉最后的\r\n
                        break
            
            if not file_data:
                self.send_json_response({
                    "error": "未找到文件数据",
                    "timestamp": datetime.now().isoformat()
                }, 400)
                return
            
            # 处理文件内容
            content = self.extract_file_content(file_data, file_type)
            
            self.send_json_response({
                "content": content,
                "filename": filename,
                "size": len(file_data),
                "type": file_type,
                "extractedLength": len(content)
            })
            
        except Exception as e:
            self.send_json_response({
                "error": "文件处理失败",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500)
    
    def handle_analyze_url(self):
        """URL分析处理"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            url = data.get('url', '')
            if not url:
                self.send_json_response({
                    "error": "URL是必需的",
                    "timestamp": datetime.now().isoformat()
                }, 400)
                return
            
            # 分析网页
            result = self.analyze_web_page(url)
            
            self.send_json_response({
                "title": result.get('title', '无标题'),
                "content": result.get('content', ''),
                "url": url,
                "analyzedAt": datetime.now().isoformat(),
                "contentLength": len(result.get('content', ''))
            })
            
        except Exception as e:
            self.send_json_response({
                "error": "网页分析失败",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500)
    
    def search_with_tavily(self, query):
        """Tavily搜索"""
        try:
            data = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_raw_content": False,
                "max_results": 5
            }
            
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except Exception as e:
            print(f"搜索失败: {e}")
            return None
    
    def call_tongyi_qwen(self, message, intent, file_content=None, web_content=None, search_results=None):
        """调用通义千问API"""
        try:
            # 构建系统提示
            system_prompt = "你是一个专业的AI助手，可以帮助用户进行对话、分析文档、搜索网络信息等任务。请用中文回答用户的问题。"
            
            if intent == "file" and file_content:
                system_prompt = f"你是一个专业的文档分析助手。请基于以下文档内容回答用户的问题：\n\n{file_content[:4000]}"
            elif intent == "web" and web_content:
                system_prompt = f"你是一个专业的网页内容分析助手。请基于以下网页内容回答用户的问题：\n\n{web_content[:4000]}"
            elif search_results:
                system_prompt = f"你是一个专业的搜索助手。请基于以下搜索结果回答用户的问题：\n\n{json.dumps(search_results, ensure_ascii=False, indent=2)}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            data = {
                "model": "qwen-turbo",
                "input": {"messages": messages},
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 3000
                }
            }
            
            req = urllib.request.Request(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Authorization': f'Bearer {self.dashscope_api_key}',
                    'Content-Type': 'application/json'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['output']['text']
                
        except Exception as e:
            print(f"AI调用失败: {e}")
            return f"抱歉，AI服务暂时不可用：{str(e)}"
    
    def extract_file_content(self, file_data, file_type):
        """提取文件内容"""
        try:
            if file_type == '.txt' or file_type == '.md':
                return file_data.decode('utf-8', errors='ignore')
            elif file_type == '.pdf':
                # 简单的PDF文本提取（需要PyPDF2库，这里用基础方法）
                return "PDF文件内容提取需要安装PyPDF2库"
            elif file_type == '.docx':
                # 简单的DOCX文本提取（需要python-docx库，这里用基础方法）
                return "DOCX文件内容提取需要安装python-docx库"
            else:
                return f"不支持的文件类型: {file_type}"
        except Exception as e:
            return f"文件内容提取失败: {str(e)}"
    
    def analyze_web_page(self, url):
        """分析网页内容"""
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # 简单的HTML解析
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "无标题"
            
            # 移除HTML标签
            content = re.sub(r'<[^>]+>', '', html)
            content = re.sub(r'\s+', ' ', content).strip()
            content = content[:4000]  # 限制长度
            
            return {
                "title": title,
                "content": content
            }
            
        except Exception as e:
            print(f"网页分析失败: {e}")
            return {
                "title": "分析失败",
                "content": f"无法分析网页：{str(e)}"
            }


def run_server(port=3001):
    """启动服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ChatbotAPIHandler)
    print(f"🚀 Python后端服务器启动在端口 {port}")
    print(f"📖 API文档: http://localhost:{port}/api/health")
    print("按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()

