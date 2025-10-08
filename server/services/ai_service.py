"""
AI服务（重构版）
负责构建提示词和协调模型调用，模型调用逻辑已统一到model_client
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from utils.logger import app_logger
from config import settings
from services.model_client import qwen_client


class AIService:
    """AI服务 - 重构版，只负责业务逻辑，模型调用委托给model_client"""
    
    def __init__(self):
        self.model_client = qwen_client
        app_logger.info(f"AI服务初始化（重构版） - 使用统一大语言模型客户端")
    
    def build_system_prompt(self, intent: str, file_content: Optional[str] = None, 
                          web_content: Optional[str] = None, search_results: Optional[Dict] = None,
                          full_context: Optional[str] = None) -> str:
        """构建系统提示词"""
        
        base_prompt = "你是一个专业的AI助手，可以帮助用户进行对话、分析文档、搜索网络信息等任务。请用中文回答用户的问题，回答要准确、有用、友好。请确保回答内容积极正面，符合社会价值观。"
        
        # 添加完整上下文（包含所有记忆信息）
        if full_context:
            base_prompt += "\n\n" + full_context
        
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
                "6. 请确保回答内容积极正面，符合社会价值观\n"
                "7. 如果遇到网页访问错误（如反爬虫保护），请清晰地向用户解释问题，并提供解决建议：\n"
                "   - 建议用户使用搜索功能来查找相关信息\n"
                "   - 或者建议用户直接复制网页内容后提问\n"
                "   - 或者尝试访问其他新闻源"
            )
            if web_content:
                # 检查是否是错误信息
                if web_content.startswith("错误："):
                    system_prompt += f"\n\n网页访问状态：\n{web_content}\n\n请向用户解释这个问题，并提供有用的建议。"
                else:
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 打印完整的对话消息（只打印一次，包含当前用户消息）
        app_logger.info("=" * 100)
        app_logger.info("🤖 [AI-SERVICE] 最终喂给大语言模型的完整Prompt:")
        app_logger.info("=" * 100)
        app_logger.info("📄 [AI-SERVICE] System Message (系统提示词):")
        app_logger.info(f"{system_prompt}")
        app_logger.info("=" * 50)
        app_logger.info("📄 [AI-SERVICE] User Message (当前用户消息):")
        app_logger.info(f"{user_message}")
        app_logger.info("=" * 100)
        
        return messages
    
    async def generate_response(self, user_message: str, intent: str = "normal", 
                              file_content: Optional[str] = None, 
                              web_content: Optional[str] = None, 
                              search_results: Optional[Dict] = None,
                              full_context: Optional[str] = None) -> str:
        """
        生成AI响应
        
        Args:
            user_message: 用户消息
            intent: 意图类型
            file_content: 文件内容
            web_content: 网页内容
            search_results: 搜索结果
            full_context: 完整上下文（包含记忆）
            
        Returns:
            AI响应文本
        """
        try:
            app_logger.info(f"开始生成AI响应，意图: {intent}")
            
            # 构建系统提示词
            system_prompt = self.build_system_prompt(intent, file_content, web_content, search_results, full_context)
            
            # 构建消息列表
            messages = self.build_messages(user_message, system_prompt)
            
            # 调用模型客户端
            response = await self.model_client.generate_text(messages)
            
            app_logger.info(f"AI响应生成完成，响应长度: {len(response)}")
            return response
        
        except Exception as e:
            app_logger.error(f"AI响应生成失败: {e}")
            raise
    
    async def generate_stream_response(
        self,
        user_message: str,
        intent: str = "chat",
        file_content: Optional[str] = None,
        web_content: Optional[str] = None,
        search_results: Optional[Dict[str, Any]] = None,
        full_context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式AI响应
        
        Args:
            user_message: 用户消息
            intent: 意图类型
            file_content: 文件内容
            web_content: 网页内容
            search_results: 搜索结果
            full_context: 完整上下文
            
        Yields:
            文本片段
        """
        try:
            app_logger.info(f"开始生成流式AI响应，意图: {intent}")
            
            # 构建系统提示词
            system_prompt = self.build_system_prompt(intent, file_content, web_content, search_results, full_context)
            
            # 构建消息列表
            messages = self.build_messages(user_message, system_prompt)
            
            # 使用模型客户端的流式生成
            async for chunk in self.model_client.generate_text_stream(messages):
                yield chunk
            
            app_logger.info(f"流式AI响应生成完成，意图: {intent}")
        
        except Exception as e:
            app_logger.error(f"流式AI响应生成失败: {e}")
            yield f"错误: {str(e)}"


# 全局AI服务实例
ai_service = AIService()
