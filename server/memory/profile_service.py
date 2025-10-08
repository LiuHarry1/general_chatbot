"""
User Profile Service
Intelligent extraction and management of user preferences and identity information
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from utils.logger import app_logger
from services.ai_service import ai_service
from memory.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class ProfileService:
    """User profile service"""
    
    def __init__(self):
        # 偏好提取关键词
        self.preference_keywords = [
            "我喜欢", "我不喜欢", "我讨厌", "我爱", "我恨",
            "我是", "我在", "我的", "我想", "我希望", "我需要",
            "我今年", "我住在", "我的职业", "我的工作", "我的爱好",
            "我的兴趣", "我的名字", "我叫", "我来自"
        ]
        
        # 身份信息关键词
        self.identity_keywords = {
            "name": ["我叫", "我的名字", "我是", "我姓"],
            "age": ["我今年", "我的年龄", "我", "岁"],
            "location": ["我住在", "我来自", "我在", "我的城市"],
            "job": ["我的职业", "我是做", "我是一名", "我的工作"],
            "education": ["我的学历", "我毕业于", "我的专业"],
            "hobby": ["我的爱好", "我喜欢", "我感兴趣", "我的兴趣"],
            "family": ["我的家人", "我的父母", "我的孩子", "我的配偶"]
        }
        
        # 情感倾向关键词
        self.emotion_keywords = {
            "positive": ["喜欢", "爱", "好", "棒", "优秀", "满意", "开心", "高兴"],
            "negative": ["讨厌", "不喜欢", "不好", "差", "糟糕", "失望", "生气", "难过"],
            "neutral": ["一般", "还行", "可以", "无所谓", "随便"]
        }
        
        # 沟通风格关键词
        self.communication_style_keywords = {
            "formal": ["您好", "请", "谢谢", "不好意思", "请问"],
            "casual": ["嗨", "嘿", "哈哈", "嗯", "哦"],
            "direct": ["直接", "简单", "明确", "具体"],
            "detailed": ["详细", "具体", "仔细", "全面"]
        }
        
        app_logger.info("ProfileService initialized")
    
    async def extract_user_preferences(
        self,
        user_id: str,
        message: str,
        conversation_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        从消息中提取用户偏好和身份信息
        
        Args:
            user_id: 用户ID
            message: 用户消息
            conversation_context: 对话上下文
            
        Returns:
            提取到的用户信息
        """
        try:
            # 检测是否包含偏好信号
            has_signal = any(keyword in message for keyword in self.preference_keywords)
            
            if not has_signal:
                return {}
            
            # 使用AI提取用户信息
            extracted_info = await self._extract_with_ai(message, conversation_context)
            
            if extracted_info:
                # 更新用户画像
                await self._update_user_profile(user_id, extracted_info)
                app_logger.info(f"提取到用户信息: {user_id} - {extracted_info}")
            
            return extracted_info
            
        except Exception as e:
            app_logger.error(f"提取用户偏好失败: {e}")
            return {}
    
    async def _extract_with_ai(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """使用AI提取用户信息"""
        try:
            context_info = ""
            if context:
                user_id = context.get('user_id', '')
                turn_count = context.get('turn_count', 0)
                context_info = f"\n\n对话上下文：用户ID={user_id}，对话轮数={turn_count}"
            
            prompt = f"""
请从以下用户消息中提取用户偏好、习惯、兴趣、身份信息等。

要求：
1. 如果消息中包含"我是"、"我叫"、"我的名字是"等，请提取姓名
2. 如果包含"我今年"、"我的年龄是"等，请提取年龄
3. 如果包含"我住在"、"我来自"等，请提取居住地
4. 如果包含"我的职业是"、"我是一名"、"我是做"等，请提取职业
5. 如果包含"我喜欢"、"我爱"、"我讨厌"、"我不喜欢"等，请提取偏好
6. 如果包含"我的爱好是"、"我感兴趣"等，请提取兴趣
7. 分析用户的沟通风格（正式/随意/直接/详细）
8. 评估信息的可信度（0-1）

请以JSON格式返回提取到的信息，例如：
{{
    "identity": {{
        "name": "张三",
        "age": 25,
        "location": "北京",
        "job": "软件工程师",
        "education": "本科"
    }},
    "preferences": ["喜欢咖啡", "不喜欢甜饮料", "喜欢看电影"],
    "interests": ["编程", "电影", "旅行"],
    "communication_style": "友好、直接",
    "confidence": 0.9,
    "extracted_at": "{datetime.now().isoformat()}"
}}

如果未提取到任何信息，请返回空JSON对象 {{}}.

用户消息: "{message}"
{context_info}

请生成提取结果：
"""
            
            # 调用AI服务
            ai_response = await ai_service.generate_response(
                user_message=prompt,
                intent="normal",
                file_content=None,
                web_content=None,
                search_results=None,
                full_context=""  # 用户信息提取不需要历史记忆
            )
            
            # 解析JSON响应
            try:
                extracted_data = json.loads(ai_response)
                return extracted_data
            except json.JSONDecodeError:
                app_logger.error(f"AI响应JSON解析失败: {ai_response}")
                return {}
            
        except Exception as e:
            app_logger.error(f"AI提取用户信息失败: {e}")
            return {}
    
    async def _update_user_profile(self, user_id: str, new_data: Dict[str, Any]):
        """更新用户画像"""
        try:
            # 获取现有画像
            existing_profile = await redis_manager.get_user_profile(user_id)
            
            # 合并身份信息
            if "identity" in new_data and isinstance(new_data["identity"], dict):
                existing_identity = existing_profile.get("identity", {})
                existing_identity.update(new_data["identity"])
                existing_profile["identity"] = existing_identity
            
            # 合并偏好
            if "preferences" in new_data and isinstance(new_data["preferences"], list):
                existing_preferences = existing_profile.get("preferences", [])
                for pref in new_data["preferences"]:
                    if pref not in existing_preferences:
                        existing_preferences.append(pref)
                existing_profile["preferences"] = existing_preferences
            
            # 合并兴趣
            if "interests" in new_data and isinstance(new_data["interests"], list):
                existing_interests = existing_profile.get("interests", [])
                for interest in new_data["interests"]:
                    if interest not in existing_interests:
                        existing_interests.append(interest)
                existing_profile["interests"] = existing_interests
            
            # 更新沟通风格
            if "communication_style" in new_data and new_data["communication_style"]:
                existing_profile["communication_style"] = new_data["communication_style"]
            
            # 更新置信度
            if "confidence" in new_data:
                existing_profile["confidence"] = new_data["confidence"]
            
            # 添加提取时间
            existing_profile["last_extracted"] = datetime.now().isoformat()
            
            # 保存更新后的画像
            await redis_manager.set_user_profile(user_id, existing_profile)
            
            app_logger.info(f"用户画像已更新: {user_id}")
            
        except Exception as e:
            app_logger.error(f"更新用户画像失败: {e}")
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户完整画像"""
        try:
            profile = await redis_manager.get_user_profile(user_id)
            return profile
        except Exception as e:
            app_logger.error(f"获取用户画像失败: {e}")
            return {}
    
    async def build_contextual_prompt(
        self,
        user_id: str,
        current_message: str
    ) -> str:
        """构建个性化上下文提示词"""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return ""
            
            context_parts = ["\n\n以下是关于用户的一些已知信息，请在对话中自然地利用这些信息，让用户感受到你认识他们："]
            
            # 身份信息
            if profile.get("identity"):
                identity = profile["identity"]
                identity_parts = []
                
                if identity.get("name"):
                    identity_parts.append(f"姓名：{identity['name']}")
                if identity.get("age"):
                    identity_parts.append(f"年龄：{identity['age']}岁")
                if identity.get("location"):
                    identity_parts.append(f"居住地：{identity['location']}")
                if identity.get("job"):
                    identity_parts.append(f"职业：{identity['job']}")
                if identity.get("education"):
                    identity_parts.append(f"学历：{identity['education']}")
                
                if identity_parts:
                    context_parts.append("【用户身份】")
                    context_parts.extend(identity_parts)
            
            # 偏好信息
            if profile.get("preferences"):
                context_parts.append(f"【用户偏好】{', '.join(profile['preferences'])}")
            
            # 兴趣信息
            if profile.get("interests"):
                context_parts.append(f"【用户兴趣】{', '.join(profile['interests'])}")
            
            # 沟通风格
            if profile.get("communication_style"):
                context_parts.append(f"【沟通风格】{profile['communication_style']}")
            
            # 置信度信息
            if profile.get("confidence"):
                confidence = profile["confidence"]
                if confidence > 0.8:
                    context_parts.append("【信息可信度】高")
                elif confidence > 0.6:
                    context_parts.append("【信息可信度】中等")
                else:
                    context_parts.append("【信息可信度】较低")
            
            context_parts.append("\n请在回答时，结合上述信息，提供更个性化和连贯的回复。")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            app_logger.error(f"构建上下文提示词失败: {e}")
            return ""
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """获取用户洞察"""
        try:
            profile = await self.get_user_profile(user_id)
            
            insights = {
                "profile_completeness": self._calculate_profile_completeness(profile),
                "preference_diversity": self._calculate_preference_diversity(profile),
                "communication_style": profile.get("communication_style", "未知"),
                "activity_level": self._calculate_activity_level(profile),
                "last_updated": profile.get("last_updated", "未知")
            }
            
            return insights
            
        except Exception as e:
            app_logger.error(f"获取用户洞察失败: {e}")
            return {}
    
    def _calculate_profile_completeness(self, profile: Dict[str, Any]) -> float:
        """计算画像完整度"""
        total_fields = 0
        filled_fields = 0
        
        # 身份信息
        identity = profile.get("identity", {})
        identity_fields = ["name", "age", "location", "job", "education"]
        for field in identity_fields:
            total_fields += 1
            if identity.get(field):
                filled_fields += 1
        
        # 偏好和兴趣
        if profile.get("preferences"):
            filled_fields += 1
        total_fields += 1
        
        if profile.get("interests"):
            filled_fields += 1
        total_fields += 1
        
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_preference_diversity(self, profile: Dict[str, Any]) -> float:
        """计算偏好多样性"""
        preferences = profile.get("preferences", [])
        interests = profile.get("interests", [])
        
        total_items = len(preferences) + len(interests)
        
        if total_items == 0:
            return 0.0
        elif total_items <= 3:
            return 0.3
        elif total_items <= 6:
            return 0.6
        else:
            return 1.0
    
    def _calculate_activity_level(self, profile: Dict[str, Any]) -> str:
        """计算活跃度等级"""
        usage_freq = profile.get("usage_frequency", {})
        daily_count = usage_freq.get("daily", 0)
        
        if daily_count >= 10:
            return "高"
        elif daily_count >= 5:
            return "中"
        elif daily_count >= 1:
            return "低"
        else:
            return "未知"


# 全局实例
profile_service = ProfileService()

