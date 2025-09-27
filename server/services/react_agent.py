"""
React Agent服务
实现ReAct (Reasoning + Acting) 模式的智能代理
能够自主决定是否需要搜索、分析文件、处理链接等
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


class ActionType(Enum):
    """行动类型枚举"""
    SEARCH = "search"
    ANALYZE_FILE = "analyze_file"
    ANALYZE_URL = "analyze_url"
    RESPOND = "respond"
    ASK_CLARIFICATION = "ask_clarification"


@dataclass
class Thought:
    """思考过程"""
    reasoning: str
    confidence: float  # 0-1之间的置信度


@dataclass
class Action:
    """行动定义"""
    type: ActionType
    parameters: Dict[str, Any]
    reasoning: str


@dataclass
class Observation:
    """观察结果"""
    content: str
    source: str
    metadata: Dict[str, Any]


class ReactAgent:
    """React Agent实现"""
    
    def __init__(self):
        self.max_iterations = 3
        self.search_service = search_service
        self.file_processor = file_processor
        self.web_analyzer = web_analyzer
        
    def analyze_query(self, user_message: str, attachments: List[Dict] = None) -> Thought:
        """分析用户查询，决定需要采取的行动"""
        reasoning_parts = []
        confidence = 0.0
        
        # 检查是否包含需要实时信息的查询
        real_time_indicators = [
            "最新", "最近", "现在", "今天", "本周", "本月", "当前",
            "news", "latest", "recent", "current", "today", "now",
            "top", "排行", "热门", "trending", "popular"
        ]
        
        # 检查是否包含搜索相关词汇
        search_indicators = [
            "搜索", "查找", "寻找", "提供", "给我", "推荐",
            "search", "find", "look up", "provide", "give me", "recommend"
        ]
        
        # 检查是否包含特定领域查询
        domain_indicators = {
            "娱乐": ["娱乐", "明星", "电影", "音乐", "综艺", "entertainment", "celebrity", "movie", "music"],
            "科技": ["科技", "技术", "AI", "人工智能", "technology", "tech", "artificial intelligence"],
            "体育": ["体育", "足球", "篮球", "比赛", "sports", "football", "basketball", "game"],
            "财经": ["财经", "股票", "经济", "投资", "finance", "stock", "economy", "investment"],
            "新闻": ["新闻", "资讯", "报道", "news", "information", "report"]
        }
        
        # 分析查询内容
        message_lower = user_message.lower()
        
        # 检查实时信息需求
        has_realtime = any(indicator in message_lower for indicator in real_time_indicators)
        if has_realtime:
            reasoning_parts.append("查询包含实时信息需求")
            confidence += 0.3
        
        # 检查搜索需求
        has_search = any(indicator in message_lower for indicator in search_indicators)
        if has_search:
            reasoning_parts.append("查询包含搜索需求")
            confidence += 0.2
        
        # 检查领域特定需求
        detected_domains = []
        for domain, keywords in domain_indicators.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_domains.append(domain)
                confidence += 0.1
        
        if detected_domains:
            reasoning_parts.append(f"检测到领域需求: {', '.join(detected_domains)}")
        
        # 检查附件
        if attachments:
            file_attachments = [att for att in attachments if att.get("type") == "file"]
            url_attachments = [att for att in attachments if att.get("type") == "url"]
            
            if file_attachments:
                reasoning_parts.append("检测到文件附件，需要分析文件内容")
                confidence += 0.2
            
            if url_attachments:
                reasoning_parts.append("检测到URL附件，需要分析网页内容")
                confidence += 0.2
        
        # 检查是否需要澄清
        unclear_indicators = ["什么", "如何", "为什么", "哪里", "什么时候", "who", "what", "how", "why", "where", "when"]
        needs_clarification = any(indicator in message_lower for indicator in unclear_indicators) and confidence < 0.3
        
        if needs_clarification:
            reasoning_parts.append("查询可能需要澄清")
            confidence = max(0.1, confidence)
        
        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "常规对话查询"
        confidence = min(1.0, confidence)
        
        return Thought(reasoning=reasoning, confidence=confidence)
    
    def decide_action(self, thought: Thought, user_message: str, attachments: List[Dict] = None) -> Action:
        """基于思考结果决定行动"""
        
        # 如果有文件附件，优先分析文件
        if attachments:
            file_attachments = [att for att in attachments if att.get("type") == "file"]
            if file_attachments:
                return Action(
                    type=ActionType.ANALYZE_FILE,
                    parameters={"attachments": file_attachments},
                    reasoning="检测到文件附件，需要分析文件内容"
                )
            
            url_attachments = [att for att in attachments if att.get("type") == "url"]
            if url_attachments:
                return Action(
                    type=ActionType.ANALYZE_URL,
                    parameters={"attachments": url_attachments},
                    reasoning="检测到URL附件，需要分析网页内容"
                )
        
        # 如果置信度高且包含搜索指标，执行搜索
        if thought.confidence >= 0.4 and any(keyword in user_message.lower() for keyword in 
            ["最新", "新闻", "搜索", "提供", "给我", "latest", "news", "search", "provide"]):
            return Action(
                type=ActionType.SEARCH,
                parameters={"query": user_message},
                reasoning=f"高置信度搜索需求: {thought.reasoning}"
            )
        
        # 如果查询模糊且置信度低，请求澄清
        if thought.confidence < 0.3 and any(keyword in user_message.lower() for keyword in 
            ["什么", "如何", "为什么", "what", "how", "why"]):
            return Action(
                type=ActionType.ASK_CLARIFICATION,
                parameters={"query": user_message},
                reasoning="查询需要澄清"
            )
        
        # 默认直接回答
        return Action(
            type=ActionType.RESPOND,
            parameters={"query": user_message},
            reasoning="常规对话，直接回答"
        )
    
    async def execute_action(self, action: Action) -> Observation:
        """执行行动并返回观察结果"""
        try:
            if action.type == ActionType.SEARCH:
                app_logger.info(f"执行搜索行动: {action.parameters['query']}")
                search_results = await self.search_service.search_with_fallback(action.parameters['query'])
                if search_results:
                    return Observation(
                        content=json.dumps(search_results, ensure_ascii=False, indent=2),
                        source="tavily_search",
                        metadata={"query": action.parameters['query'], "results_count": search_results.get('total_results', 0)}
                    )
                else:
                    return Observation(
                        content="搜索服务暂时不可用",
                        source="error",
                        metadata={"query": action.parameters['query']}
                    )
            
            elif action.type == ActionType.ANALYZE_FILE:
                app_logger.info("执行文件分析行动")
                file_contents = []
                for attachment in action.parameters['attachments']:
                    if 'data' in attachment and 'content' in attachment['data']:
                        file_contents.append(attachment['data']['content'])
                
                return Observation(
                    content="\n\n".join(file_contents),
                    source="file_analysis",
                    metadata={"file_count": len(file_contents)}
                )
            
            elif action.type == ActionType.ANALYZE_URL:
                app_logger.info("执行URL分析行动")
                url_contents = []
                for attachment in action.parameters['attachments']:
                    if 'data' in attachment and 'content' in attachment['data']:
                        url_contents.append(attachment['data']['content'])
                
                return Observation(
                    content="\n\n".join(url_contents),
                    source="url_analysis",
                    metadata={"url_count": len(url_contents)}
                )
            
            elif action.type == ActionType.ASK_CLARIFICATION:
                return Observation(
                    content="请提供更具体的问题，以便我为您提供更准确的帮助。",
                    source="clarification",
                    metadata={}
                )
            
            else:  # RESPOND
                return Observation(
                    content="",
                    source="direct_response",
                    metadata={}
                )
                
        except Exception as e:
            app_logger.error(f"执行行动失败: {e}")
            return Observation(
                content=f"执行行动时发生错误: {str(e)}",
                source="error",
                metadata={"error": str(e)}
            )
    
    def should_continue(self, iteration: int, last_observation: Observation) -> bool:
        """判断是否应该继续迭代"""
        if iteration >= self.max_iterations:
            return False
        
        # 如果上次观察是错误或澄清请求，停止迭代
        if last_observation.source in ["error", "clarification"]:
            return False
        
        # 如果获得了搜索结果或分析结果，停止迭代
        if last_observation.source in ["tavily_search", "file_analysis", "url_analysis"]:
            return False
        
        return True
    
    async def process_query(self, user_message: str, attachments: List[Dict] = None) -> Tuple[str, str, Optional[Dict]]:
        """
        处理用户查询的主方法
        返回: (intent, content, search_results)
        """
        app_logger.info(f"React Agent开始处理查询: {user_message}")
        
        # 第一步：分析查询
        thought = self.analyze_query(user_message, attachments)
        app_logger.info(f"思考结果: {thought.reasoning} (置信度: {thought.confidence})")
        
        # 第二步：决定行动
        action = self.decide_action(thought, user_message, attachments)
        app_logger.info(f"决定行动: {action.type.value} - {action.reasoning}")
        
        # 第三步：执行行动
        observation = await self.execute_action(action)
        app_logger.info(f"观察结果: {observation.source} - {len(observation.content)} 字符")
        
        # 确定意图和内容
        if action.type == ActionType.SEARCH and observation.source == "tavily_search":
            search_results = json.loads(observation.content) if observation.content else None
            return "search", user_message, search_results
        elif action.type == ActionType.ANALYZE_FILE:
            return "file", observation.content, None
        elif action.type == ActionType.ANALYZE_URL:
            return "web", observation.content, None
        else:
            return "normal", user_message, None


# 全局Agent实例
react_agent = ReactAgent()
