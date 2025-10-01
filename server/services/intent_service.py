"""
基于LLM的智能意图识别服务
使用大语言模型来判断用户意图，支持对话历史分析
"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import app_logger
from services.search_service import search_service
from services.file_processor import file_processor
from services.web_analyzer import web_analyzer
from services.ai_service import ai_service


class IntentType(Enum):
    """意图类型枚举"""
    FILE = "file"           # 文件分析
    WEB = "web"            # URL内容分析
    SEARCH = "search"      # 网络搜索（LLM判断）
    CODE = "code"          # Python代码执行（LLM判断）
    NORMAL = "normal"      # 普通对话


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    content: str
    search_results: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    reasoning: str = ""


class LLMBasedIntentService:
    """基于LLM的智能意图识别服务"""
    
    def __init__(self):
        self.search_service = search_service
        self.file_processor = file_processor
        self.web_analyzer = web_analyzer
        self.ai_service = ai_service
        
        # URL模式
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
    
    def detect_urls(self, text: str) -> List[str]:
        """检测文本中的URL"""
        return self.url_pattern.findall(text)
    
    async def analyze_with_llm(self, message: str, recent_conversations: List[Dict] = None) -> Tuple[str, str, float]:
        """
        使用LLM分析用户意图
        返回: (intent, reasoning, confidence)
        """
        # 构建对话历史上下文
        conversation_context = ""
        if recent_conversations:
            conversation_context = "\n最近的对话历史：\n"
            for conv in recent_conversations[-3:]:  # 最近3条对话
                conversation_context += f"用户: {conv.get('user_message', '')}\n"
                conversation_context += f"助手: {conv.get('ai_response', '')}\n\n"
        
        # 构建意图分析提示词
        intent_prompt = f"""
你是一个智能意图识别助手。请分析用户的消息和对话历史，判断用户的意图。

{conversation_context}

当前用户消息: {message}

请从以下意图中选择最合适的一个：
1. search - 用户需要搜索网络上的最新信息、实时数据、新闻、特定知识等
2. code - 用户需要执行Python代码进行数据分析、计算、报表生成、问题分析、画图、可视化、绘图等
3. normal - 普通对话，不需要特殊工具

分析要点：
- 如果用户询问最新信息、新闻、实时数据、天气、股票、汇率、特定知识查询，选择 search
- 如果用户需要执行代码进行数据分析、计算、报表生成、画图、绘图、可视化、生成图表等，选择 code  
- 如果只是普通对话、学习编程、询问概念、寻求解释、教学等，选择 normal
- 考虑对话历史的上下文，判断用户的真实需求

特别注意：
- 学习编程、询问编程概念、寻求代码解释、教学指导等属于 normal 意图
- 只有明确要求执行代码、进行数据分析、生成图表等才属于 code 意图

特别注意：
- 天气查询（如"今天天气"、"某地天气"）属于实时数据需求，应归类为 search 意图
- 股票、汇率、新闻等实时信息查询也应归类为 search 意图

特别注意：
- 画图、绘图、可视化、生成图表、绘制函数图、制作图表等需求都应该归类为 code 意图
- 包括但不限于：sin图、cos图、函数图像、数据图表、统计图、流程图等

请以JSON格式回答：
{{
    "intent": "search|code|normal",
    "reasoning": "详细说明为什么选择这个意图",
    "confidence": 0.0-1.0
}}
"""
        
        try:
            # 调用LLM进行意图分析
            response = await self.ai_service.generate_response(
                user_message=intent_prompt,
                intent="normal",  # 意图分析本身是普通对话
                file_content=None,
                web_content=None,
                search_results=None,
                user_identity={},
                contextual_prompt="",
                short_term_context=""
            )
            
            # 解析LLM响应
            try:
                # 尝试提取JSON部分
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    
                    intent = result.get('intent', 'normal')
                    reasoning = result.get('reasoning', '')
                    confidence = float(result.get('confidence', 0.8))
                    
                    return intent, reasoning, confidence
                else:
                    # 如果无法解析JSON，尝试从文本中提取意图
                    if 'search' in response.lower():
                        return 'search', 'LLM判断需要搜索', 0.7
                    elif 'code' in response.lower():
                        return 'code', 'LLM判断需要代码执行', 0.7
                    else:
                        return 'normal', 'LLM判断普通对话', 0.7
                        
            except json.JSONDecodeError:
                # JSON解析失败，使用默认逻辑
                if 'search' in response.lower():
                    return 'search', 'LLM判断需要搜索', 0.6
                elif 'code' in response.lower():
                    return 'code', 'LLM判断需要代码执行', 0.6
                else:
                    return 'normal', 'LLM判断普通对话', 0.6
                    
        except Exception as e:
            app_logger.error(f"LLM意图分析失败: {e}")
            # 降级到普通对话
            return 'normal', f'LLM分析失败，使用普通对话: {str(e)}', 0.5
    
    async def process_intent(self, message: str, attachments: List[Dict] = None, user_id: str = "default_user", recent_conversations: List[Dict] = None) -> IntentResult:
        """
        处理意图识别的主方法
        返回: IntentResult
        """
        app_logger.info(f"开始意图识别: {message}")
        
        # 1. 检查附件（区分文件和URL）
        if attachments and len(attachments) > 0:
            # 检查是否有URL类型的附件
            url_attachments = [att for att in attachments if att.get('type') == 'url']
            file_attachments = [att for att in attachments if att.get('type') == 'file' or att.get('type') != 'url']
            
            # 优先处理URL附件
            if url_attachments:
                app_logger.info("检测到URL附件，使用网页分析意图")
                try:
                    # 处理URL内容
                    web_content = ""
                    for attachment in url_attachments:
                        if attachment.get('content'):
                            web_content += f"\n\n{attachment['content']}"
                    
                    return IntentResult(
                        intent=IntentType.WEB,
                        content=web_content,
                        confidence=1.0,
                        reasoning="检测到URL附件"
                    )
                except Exception as e:
                    app_logger.error(f"处理URL附件失败: {e}")
                    return IntentResult(
                        intent=IntentType.NORMAL,
                        content=message,
                        confidence=1.0,
                        reasoning=f"URL处理失败，使用普通对话: {str(e)}"
                    )
            
            # 处理文件附件
            if file_attachments:
                app_logger.info("检测到文件附件，使用文件分析意图")
                try:
                    # 处理文件内容
                    file_content = ""
                    for attachment in file_attachments:
                        if attachment.get('content'):
                            file_content += f"\n\n文件 {attachment.get('filename', 'unknown')}:\n{attachment['content']}"
                    
                    return IntentResult(
                        intent=IntentType.FILE,
                        content=file_content,
                        confidence=1.0,
                        reasoning="检测到文件附件"
                    )
                except Exception as e:
                    app_logger.error(f"处理文件附件失败: {e}")
                    return IntentResult(
                        intent=IntentType.NORMAL,
                        content=message,
                        confidence=1.0,
                        reasoning=f"文件处理失败，使用普通对话: {str(e)}"
                    )
        
        # 2. 检查URL（优先级第二）
        urls = self.detect_urls(message)
        if urls:
            app_logger.info(f"检测到URL: {urls}")
            try:
                # 分析第一个URL
                url = urls[0]
                web_result = await self.web_analyzer.analyze_web_page(url)
                web_content = f"标题：{web_result['title']}\n\n内容：{web_result['content']}"
                
                return IntentResult(
                    intent=IntentType.WEB,
                    content=web_content,
                    confidence=1.0,
                    reasoning=f"检测到URL: {url}"
                )
            except Exception as e:
                error_msg = str(e)
                app_logger.error(f"分析URL失败: {error_msg}")
                
                # 如果是反爬虫保护错误，使用WEB意图但传递错误信息
                if "反爬虫" in error_msg or "安全验证" in error_msg:
                    return IntentResult(
                        intent=IntentType.WEB,
                        content=f"错误：{error_msg}\n\n原始问题：{message}",
                        confidence=0.8,
                        reasoning=f"URL分析遇到反爬虫保护: {url}"
                    )
                else:
                    # 其他错误，降级为普通对话
                    return IntentResult(
                        intent=IntentType.NORMAL,
                        content=f"无法访问网页 {url}，错误：{error_msg}\n\n{message}",
                        confidence=0.7,
                        reasoning=f"URL分析失败: {error_msg}"
                    )
        
        # 3. 使用LLM分析其他意图（search, code, normal）
        app_logger.info("使用LLM分析用户意图")
        try:
            llm_intent, reasoning, confidence = await self.analyze_with_llm(message, recent_conversations)
            app_logger.info(f"LLM意图分析结果: {llm_intent}, 置信度: {confidence}, 推理: {reasoning}")
            app_logger.info(f"LLM原始响应类型: {type(llm_intent)}, 值: {repr(llm_intent)}")
            
            if llm_intent == "search":
                try:
                    # 执行搜索
                    search_results = await self.search_service.search(message)
                    
                    return IntentResult(
                        intent=IntentType.SEARCH,
                        content=message,
                        search_results=search_results,
                        confidence=confidence,
                        reasoning=reasoning
                    )
                except Exception as e:
                    app_logger.error(f"搜索失败: {e}")
                    return IntentResult(
                        intent=IntentType.NORMAL,
                        content=message,
                        confidence=1.0,
                        reasoning=f"搜索失败，使用普通对话: {str(e)}"
                    )
            
            elif llm_intent == "code":
                app_logger.info("LLM判断需要Python代码执行")
                # 这里将来可以集成Python代码执行服务
                return IntentResult(
                    intent=IntentType.CODE,
                    content=message,
                    confidence=confidence,
                    reasoning=reasoning
                )
            
            else:  # normal
                app_logger.info("LLM判断普通对话")
                return IntentResult(
                    intent=IntentType.NORMAL,
                    content=message,
                    confidence=confidence,
                    reasoning=reasoning
                )
                
        except Exception as e:
            app_logger.error(f"LLM意图分析失败: {e}")
            # 降级到普通对话
            return IntentResult(
                intent=IntentType.NORMAL,
                content=message,
                confidence=0.5,
                reasoning=f"LLM分析失败，使用普通对话: {str(e)}"
            )
    
    async def process_with_memory(self, message: str, attachments: List[Dict] = None, user_id: str = "default_user") -> Tuple[IntentResult, Dict[str, Any], str, str]:
        """
        带记忆的意图处理
        返回: (intent_result, user_profile, contextual_prompt, short_term_context)
        """
        # 获取最近对话历史用于LLM意图分析
        recent_conversations = None
        try:
            # 这里需要从短期记忆获取最近对话
            # 暂时使用空列表，实际实现时需要集成短期记忆系统
            recent_conversations = []
        except Exception as e:
            app_logger.error(f"获取对话历史失败: {e}")
            recent_conversations = []
        
        # 处理意图识别（包含对话历史）
        intent_result = await self.process_intent(message, attachments, user_id, recent_conversations)
        
        # 这里可以集成长短期记忆系统
        # 暂时返回空的记忆上下文
        user_profile = {}
        contextual_prompt = ""
        short_term_context = ""
        
        # 可以根据意图类型添加特定的记忆上下文
        if intent_result.intent == IntentType.FILE:
            contextual_prompt += "\n\n用户正在分析文件内容，请根据文件内容回答问题。"
        elif intent_result.intent == IntentType.WEB:
            contextual_prompt += "\n\n用户正在分析网页内容，请根据网页内容回答问题。"
        elif intent_result.intent == IntentType.SEARCH:
            contextual_prompt += "\n\n用户正在进行网络搜索，请根据搜索结果回答问题。"
        elif intent_result.intent == IntentType.CODE:
            contextual_prompt += "\n\n用户需要执行Python代码进行数据分析或计算，请帮助编写和执行代码。"
        
        return intent_result, user_profile, contextual_prompt, short_term_context


# 全局服务实例
llm_based_intent_service = LLMBasedIntentService()
