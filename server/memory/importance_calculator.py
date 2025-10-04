"""
重要性评分计算器
智能评估对话和记忆的重要性
"""
import re
import math
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ImportanceCalculator:
    """重要性评分计算器"""
    
    def __init__(self):
        # 意图权重配置
        self.intent_weights = {
            'search': 0.4,
            'web': 0.4,
            'file': 0.4,
            'code': 0.3,
            'image': 0.3,
            'normal': 0.1,
            'greeting': 0.05,
            'goodbye': 0.05
        }
        
        # 关键词权重配置
        self.importance_keywords = {
            'high': ['重要', '关键', '必须', '紧急', '优先', '核心', '主要', '决定', '选择'],
            'medium': ['需要', '想要', '希望', '计划', '打算', '考虑', '建议', '推荐'],
            'low': ['可能', '也许', '大概', '或者', '随便', '无所谓']
        }
        
        # 个人信息关键词
        self.personal_keywords = [
            '我的', '我是', '我在', '我会', '我想', '我需要', '我喜欢', '我不喜欢',
            '我讨厌', '我爱', '我恨', '我的名字', '我今年', '我住在', '我的职业',
            '我的工作', '我的爱好', '我的兴趣', '我的家人', '我的朋友'
        ]
        
        # 情感强度关键词
        self.emotion_keywords = {
            'strong_positive': ['非常喜欢', '超级爱', '特别', '极其', '绝对', '完全'],
            'strong_negative': ['非常讨厌', '超级恨', '绝对不', '完全不能', '极其'],
            'moderate_positive': ['喜欢', '爱', '好', '不错', '可以'],
            'moderate_negative': ['讨厌', '不喜欢', '不好', '不行', '不能']
        }
    
    def calculate_conversation_importance(
        self,
        message: str,
        response: str,
        intent: str,
        user_id: str,
        conversation_context: Dict[str, Any] = None
    ) -> float:
        """
        计算对话重要性评分 (0-1)
        
        Args:
            message: 用户消息
            response: 助手回复
            intent: 对话意图
            user_id: 用户ID
            conversation_context: 对话上下文信息
            
        Returns:
            重要性评分 (0.0-1.0)
        """
        try:
            total_score = 0.0
            
            # 1. 长度因子 (0-0.25)
            length_score = self._calculate_length_score(message, response)
            total_score += length_score
            
            # 2. 意图因子 (0-0.4)
            intent_score = self._calculate_intent_score(intent)
            total_score += intent_score
            
            # 3. 关键词因子 (0-0.2)
            keyword_score = self._calculate_keyword_score(message, response)
            total_score += keyword_score
            
            # 4. 个人信息因子 (0-0.1)
            personal_score = self._calculate_personal_score(message)
            total_score += personal_score
            
            # 5. 情感强度因子 (0-0.05)
            emotion_score = self._calculate_emotion_score(message, response)
            total_score += emotion_score
            
            # 6. 上下文因子 (0-0.1)
            context_score = self._calculate_context_score(conversation_context)
            total_score += context_score
            
            # 确保评分在0-1范围内
            final_score = min(max(total_score, 0.0), 1.0)
            
            logger.debug(
                f"Importance calculation - "
                f"length: {length_score:.3f}, intent: {intent_score:.3f}, "
                f"keyword: {keyword_score:.3f}, personal: {personal_score:.3f}, "
                f"emotion: {emotion_score:.3f}, context: {context_score:.3f}, "
                f"total: {final_score:.3f}"
            )
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating conversation importance: {e}")
            return 0.1  # 默认低重要性
    
    def _calculate_length_score(self, message: str, response: str) -> float:
        """计算长度因子"""
        total_length = len(message) + len(response)
        
        if total_length > 1000:
            return 0.25
        elif total_length > 500:
            return 0.2
        elif total_length > 200:
            return 0.15
        elif total_length > 100:
            return 0.1
        else:
            return 0.05
    
    def _calculate_intent_score(self, intent: str) -> float:
        """计算意图因子"""
        return self.intent_weights.get(intent, 0.1)
    
    def _calculate_keyword_score(self, message: str, response: str) -> float:
        """计算关键词因子"""
        text = (message + " " + response).lower()
        score = 0.0
        
        # 高重要性关键词
        high_count = sum(1 for keyword in self.importance_keywords['high'] if keyword in text)
        if high_count > 0:
            score += min(0.15, high_count * 0.03)
        
        # 中重要性关键词
        medium_count = sum(1 for keyword in self.importance_keywords['medium'] if keyword in text)
        if medium_count > 0:
            score += min(0.05, medium_count * 0.01)
        
        # 低重要性关键词（负分）
        low_count = sum(1 for keyword in self.importance_keywords['low'] if keyword in text)
        if low_count > 0:
            score -= min(0.02, low_count * 0.005)
        
        return max(0.0, score)
    
    def _calculate_personal_score(self, message: str) -> float:
        """计算个人信息因子"""
        personal_count = sum(1 for keyword in self.personal_keywords if keyword in message)
        
        if personal_count >= 3:
            return 0.1
        elif personal_count >= 2:
            return 0.07
        elif personal_count >= 1:
            return 0.05
        else:
            return 0.0
    
    def _calculate_emotion_score(self, message: str, response: str) -> float:
        """计算情感强度因子"""
        text = (message + " " + response).lower()
        score = 0.0
        
        # 强情感
        strong_positive = sum(1 for keyword in self.emotion_keywords['strong_positive'] if keyword in text)
        strong_negative = sum(1 for keyword in self.emotion_keywords['strong_negative'] if keyword in text)
        
        if strong_positive > 0 or strong_negative > 0:
            score += 0.03
        
        # 中等情感
        moderate_positive = sum(1 for keyword in self.emotion_keywords['moderate_positive'] if keyword in text)
        moderate_negative = sum(1 for keyword in self.emotion_keywords['moderate_negative'] if keyword in text)
        
        if moderate_positive > 0 or moderate_negative > 0:
            score += 0.02
        
        return min(score, 0.05)
    
    def _calculate_context_score(self, context: Dict[str, Any]) -> float:
        """计算上下文因子"""
        if not context:
            return 0.0
        
        score = 0.0
        
        # 对话轮数因子
        turn_count = context.get('turn_count', 0)
        if turn_count > 10:
            score += 0.03
        elif turn_count > 5:
            score += 0.02
        elif turn_count > 2:
            score += 0.01
        
        # 时间因子（工作时间 vs 非工作时间）
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 18:  # 工作时间
            score += 0.02
        
        # 用户活跃度因子
        user_activity = context.get('user_activity_score', 0)
        if user_activity > 0.8:
            score += 0.03
        elif user_activity > 0.5:
            score += 0.02
        elif user_activity > 0.2:
            score += 0.01
        
        return min(score, 0.1)
    
    def calculate_memory_decay(
        self,
        memory: Dict[str, Any],
        current_time: datetime = None
    ) -> float:
        """
        计算记忆衰减因子
        
        Args:
            memory: 记忆数据
            current_time: 当前时间
            
        Returns:
            衰减后的重要性评分
        """
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # 获取记忆创建时间
            created_at = memory.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            # 计算时间差（天）
            age_days = (current_time - created_at).days
            
            # 基础衰减率
            base_decay_rate = 0.1  # 每天衰减10%
            
            # 访问频率补偿
            access_count = memory.get('access_count', 0)
            access_compensation = min(0.2, access_count * 0.05)
            
            # 重要性补偿（重要性越高，衰减越慢）
            importance_score = memory.get('importance_score', 0.0)
            importance_compensation = importance_score * 0.1
            
            # 计算衰减
            decay_factor = max(0.0, 1.0 - (age_days * base_decay_rate) + access_compensation + importance_compensation)
            
            # 应用衰减
            original_score = memory.get('importance_score', 0.0)
            decayed_score = original_score * decay_factor
            
            logger.debug(
                f"Memory decay calculation - "
                f"age: {age_days} days, access: {access_count}, "
                f"original: {original_score:.3f}, decayed: {decayed_score:.3f}"
            )
            
            return max(0.0, decayed_score)
            
        except Exception as e:
            logger.error(f"Error calculating memory decay: {e}")
            return memory.get('importance_score', 0.0)
    
    def should_store_in_long_term(self, importance_score: float, threshold: float = 0.6) -> bool:
        """判断是否应该存储到长期记忆"""
        return importance_score >= threshold
    
    def get_memory_priority(self, memory: Dict[str, Any]) -> str:
        """获取记忆优先级"""
        importance = memory.get('importance_score', 0.0)
        access_count = memory.get('access_count', 0)
        
        if importance >= 0.8 or access_count >= 10:
            return "high"
        elif importance >= 0.6 or access_count >= 5:
            return "medium"
        else:
            return "low"
    
    def calculate_compression_priority(
        self,
        conversation_length: int,
        token_count: int,
        max_tokens: int = 1000
    ) -> Tuple[bool, float]:
        """
        计算压缩优先级
        
        Returns:
            (should_compress, priority_score)
        """
        if token_count <= max_tokens:
            return False, 0.0
        
        # 计算压缩紧迫性
        urgency = min(1.0, (token_count - max_tokens) / max_tokens)
        
        # 对话长度因子
        length_factor = min(1.0, conversation_length / 20)  # 20轮对话为满值
        
        priority_score = (urgency * 0.7) + (length_factor * 0.3)
        
        return True, priority_score


# 全局实例
importance_calculator = ImportanceCalculator()
