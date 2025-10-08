"""
总结生成器
负责生成对话总结
"""
from typing import List, Dict, Any
import logging

from utils.logger import app_logger
from services.ai_service import ai_service

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """总结生成器 - 负责生成各种层级的对话总结"""
    
    def __init__(self):
        self.summary_layers = {
            'L1': {'max_turns': 2, 'description': '单轮对话摘要'},  # 最近2轮
            'L2': {'max_turns': 5, 'description': '多轮对话摘要'},  # 最近5轮
            'L3': {'max_turns': 10, 'description': '主题聚类摘要'}   # 最近10轮
        }
        app_logger.info("SummaryGenerator initialized")
    
    async def generate_summary_for_messages(self, messages: List[Dict[str, Any]]) -> str:
        """为消息列表生成摘要"""
        if not messages:
            return ""
        
        try:
            # 构建用于摘要的上下文
            context_parts = []
            for msg in messages:
                user_msg = msg.get('user_message', '')
                ai_response = msg.get('ai_response', '')
                if user_msg and ai_response:
                    context_parts.append(f"用户: {user_msg}")
                    context_parts.append(f"助手: {ai_response}")
            
            context = "\n".join(context_parts)
            
            # 构建摘要提示词
            prompt = f"""
请将以下对话内容总结成简洁的摘要（不超过100字）。
注意：
1. 保留关键信息和主要讨论点
2. 使用简洁的语言
3. 突出重要的事实和结论

对话内容：
{context}

请生成摘要：
"""
            
            # 调用AI服务生成摘要
            summary = await ai_service.generate_response(
                user_message=prompt,
                intent="normal",
                file_content=None,
                web_content=None,
                search_results=None,
                full_context=""  # 摘要生成不需要历史记忆
            )
            
            app_logger.info(f"✨ [SUMMARY] Generated summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            app_logger.error(f"❌ [SUMMARY] Failed to generate summary: {e}")
            return ""
    
    async def generate_layer_summary(
        self,
        layer: str,
        messages: List[Dict[str, Any]],
        previous_summary: str = ""
    ) -> str:
        """生成指定层级的摘要"""
        try:
            layer_config = self.summary_layers.get(layer, {})
            max_turns = layer_config.get('max_turns', 5)
            description = layer_config.get('description', '')
            
            # 只使用最近的N轮对话
            recent_messages = messages[-max_turns:] if len(messages) > max_turns else messages
            
            # 构建对话内容
            context_parts = []
            for msg in recent_messages:
                user_msg = msg.get('user_message', '')
                ai_response = msg.get('ai_response', '')
                if user_msg and ai_response:
                    context_parts.append(f"用户: {user_msg}")
                    context_parts.append(f"助手: {ai_response}")
            
            context = "\n".join(context_parts)
            
            # 如果有上一层的摘要，包含在prompt中
            previous_context = ""
            if previous_summary:
                previous_context = f"\n\n上一层摘要：\n{previous_summary}\n"
            
            # 构建提示词
            prompt = f"""
请为以下对话生成{description}（{layer}层）。
要求：
1. 简洁清晰，不超过150字
2. 保留关键信息和讨论要点
3. 如果有上一层摘要，基于其基础上进行补充和总结
{previous_context}
最近对话内容：
{context}

请生成{layer}层摘要：
"""
            
            # 调用AI服务生成摘要
            summary = await ai_service.generate_response(
                user_message=prompt,
                intent="normal",
                file_content=None,
                web_content=None,
                search_results=None,
                full_context=""
            )
            
            app_logger.info(f"✨ [SUMMARY-{layer}] Generated layer summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            app_logger.error(f"❌ [SUMMARY-{layer}] Failed to generate layer summary: {e}")
            return ""


# 全局实例
summary_generator = SummaryGenerator()

