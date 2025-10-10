"""
Redis Cache Manager
Modern cache and user profile storage implementation
"""
import json
import redis
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis cache manager"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_conn = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.host = host
        self.port = port
        self.db = db
        
        # 键前缀配置
        self.key_prefixes = {
            "user_profile": "profile:",
            "session_cache": "session:",
            "conversation_cache": "conv:",
            "user_preferences": "prefs:",
            "memory_index": "mem_idx:",
            "temp_data": "temp:"
        }
        
        logger.info(f"RedisManager initialized: {host}:{port}/{db}")
    
    async def set_user_profile(self, user_id: str, profile_data: Dict[str, Any], ttl: int = 86400 * 7) -> bool:
        """设置用户画像"""
        try:
            key = f"{self.key_prefixes['user_profile']}{user_id}"
            
            # 添加更新时间
            profile_data["last_updated"] = datetime.now().isoformat()
            
            # 序列化并存储
            profile_json = json.dumps(profile_data, ensure_ascii=False)
            result = self.redis_conn.setex(key, ttl, profile_json)
            
            if result:
                logger.info(f"User profile stored for user: {user_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error storing user profile for {user_id}: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户画像"""
        try:
            key = f"{self.key_prefixes['user_profile']}{user_id}"
            profile_json = self.redis_conn.get(key)
            
            if profile_json:
                profile = json.loads(profile_json)
                logger.debug(f"User profile retrieved for user: {user_id}")
                return profile
            return {}
            
        except Exception as e:
            logger.error(f"Error retrieving user profile for {user_id}: {e}")
            return {}
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """更新用户偏好"""
        try:
            # 获取现有画像
            profile = await self.get_user_profile(user_id)
            
            # 合并偏好
            if "preferences" not in profile:
                profile["preferences"] = []
            
            existing_prefs = profile["preferences"]
            for pref in preferences.get("preferences", []):
                if pref not in existing_prefs:
                    existing_prefs.append(pref)
            
            # 更新其他字段
            for key, value in preferences.items():
                if key != "preferences":
                    profile[key] = value
            
            # 保存更新后的画像
            return await self.set_user_profile(user_id, profile)
            
        except Exception as e:
            logger.error(f"Error updating user preferences for {user_id}: {e}")
            return False
    
    async def cache_conversation(self, conversation_id: str, messages: List[Dict[str, Any]], ttl: int = 3600) -> bool:
        """缓存对话内容"""
        try:
            key = f"{self.key_prefixes['conversation_cache']}{conversation_id}"
            
            # 只保留最近的消息
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            
            conversation_data = {
                "messages": recent_messages,
                "cached_at": datetime.now().isoformat(),
                "message_count": len(messages)
            }
            
            conversation_json = json.dumps(conversation_data, ensure_ascii=False)
            result = self.redis_conn.setex(key, ttl, conversation_json)
            
            if result:
                logger.debug(f"Conversation cached: {conversation_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error caching conversation {conversation_id}: {e}")
            return False
    
    async def get_cached_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的对话"""
        try:
            key = f"{self.key_prefixes['conversation_cache']}{conversation_id}"
            conversation_json = self.redis_conn.get(key)
            
            if conversation_json:
                conversation = json.loads(conversation_json)
                logger.debug(f"Cached conversation retrieved: {conversation_id}")
                return conversation
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached conversation {conversation_id}: {e}")
            return None
    
    async def cache_session_data(self, session_id: str, data: Dict[str, Any], ttl: int = 1800) -> bool:
        """缓存会话数据"""
        try:
            key = f"{self.key_prefixes['session_cache']}{session_id}"
            
            session_data = {
                **data,
                "cached_at": datetime.now().isoformat()
            }
            
            session_json = json.dumps(session_data, ensure_ascii=False)
            result = self.redis_conn.setex(key, ttl, session_json)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error caching session data {session_id}: {e}")
            return False
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        try:
            key = f"{self.key_prefixes['session_cache']}{session_id}"
            session_json = self.redis_conn.get(key)
            
            if session_json:
                return json.loads(session_json)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving session data {session_id}: {e}")
            return None
    
    async def set_memory_index(self, memory_id: str, index_data: Dict[str, Any], ttl: int = 86400) -> bool:
        """设置记忆索引"""
        try:
            key = f"{self.key_prefixes['memory_index']}{memory_id}"
            
            index_data["indexed_at"] = datetime.now().isoformat()
            index_json = json.dumps(index_data, ensure_ascii=False)
            
            result = self.redis_conn.setex(key, ttl, index_json)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error setting memory index {memory_id}: {e}")
            return False
    
    async def get_memory_index(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆索引"""
        try:
            key = f"{self.key_prefixes['memory_index']}{memory_id}"
            index_json = self.redis_conn.get(key)
            
            if index_json:
                return json.loads(index_json)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving memory index {memory_id}: {e}")
            return None
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        try:
            pattern = f"{self.key_prefixes['memory_index']}*"
            keys = self.redis_conn.keys(pattern)
            
            user_memories = 0
            total_importance = 0.0
            recent_access = 0
            
            for key in keys:
                index_data = self.redis_conn.get(key)
                if index_data:
                    data = json.loads(index_data)
                    if data.get("user_id") == user_id:
                        user_memories += 1
                        total_importance += data.get("importance_score", 0.0)
                        
                        # 检查最近访问
                        last_accessed = data.get("last_accessed")
                        if last_accessed:
                            last_time = datetime.fromisoformat(last_accessed)
                            if (datetime.now() - last_time).days < 7:
                                recent_access += 1
            
            avg_importance = total_importance / user_memories if user_memories > 0 else 0.0
            
            return {
                "total_memories": user_memories,
                "average_importance": avg_importance,
                "recent_access_count": recent_access
            }
            
        except Exception as e:
            logger.error(f"Error getting user memory stats for {user_id}: {e}")
            return {}
    
    async def clear_user_data(self, user_id: str) -> bool:
        """清除用户所有数据"""
        try:
            # 清除用户画像
            profile_key = f"{self.key_prefixes['user_profile']}{user_id}"
            self.redis_conn.delete(profile_key)
            
            # 清除用户相关的记忆索引
            pattern = f"{self.key_prefixes['memory_index']}*"
            keys = self.redis_conn.keys(pattern)
            
            for key in keys:
                index_data = self.redis_conn.get(key)
                if index_data:
                    data = json.loads(index_data)
                    if data.get("user_id") == user_id:
                        self.redis_conn.delete(key)
            
            logger.info(f"Cleared all data for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing user data for {user_id}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            self.redis_conn.ping()
            info = self.redis_conn.info()
            
            return {
                "status": "ok",
                "message": "Redis is reachable",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Redis connection failed: {e}",
                "host": self.host,
                "port": self.port,
                "db": self.db
            }
    
    async def store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """存储单轮对话到指定 conversation_id"""
        try:
            timestamp = datetime.now().isoformat()
            
            conversation_data = {
                "message": message,
                "response": response,
                "timestamp": timestamp,
                "metadata": json.dumps(metadata or {}, ensure_ascii=False)
            }
            
            # 使用 conversation_id 作为键
            conversation_key = f"conversation:{user_id}:{conversation_id}"
            
            # 将对话数据序列化为 JSON 并添加到列表头部（最新的在前）
            conversation_json = json.dumps(conversation_data, ensure_ascii=False)
            self.redis_conn.lpush(conversation_key, conversation_json)
            
            # 限制列表长度，只保留最近 100 轮对话
            self.redis_conn.ltrim(conversation_key, 0, 99)
            
            # 设置过期时间（7天）
            self.redis_conn.expire(conversation_key, 7 * 24 * 3600)
            
            logger.info(f"Stored conversation for user {user_id}, conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return False
    
    async def get_recent_conversations(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """获取当前对话的最近几轮交互"""
        try:
            conversation_key = f"conversation:{user_id}:{conversation_id}"
            
            # 获取最近 limit 条记录（LRANGE 返回从最新到最旧，因为用的是 LPUSH）
            # 索引 0 是最新的，limit-1 是第 limit 条
            conversation_list = self.redis_conn.lrange(conversation_key, 0, limit - 1)
            
            conversations = []
            for conv_json in conversation_list:
                try:
                    # 解析 JSON 数据
                    conv_data = json.loads(conv_json)
                    conversations.append({
                        "conversation_id": conversation_id,
                        "message": conv_data.get("message", ""),
                        "response": conv_data.get("response", ""),
                        "timestamp": conv_data.get("timestamp", ""),
                        "metadata": conv_data.get("metadata", "{}")
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse conversation data: {e}")
                    continue
            
            # 反转列表，让最旧的在前，最新的在后（时间正序）
            conversations.reverse()
            
            logger.debug(f"Retrieved {len(conversations)} conversations for {user_id}:{conversation_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get recent conversations for {user_id}:{conversation_id}: {e}")
            return []
    
    async def get_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        layer: str = "L1"
    ) -> Optional[str]:
        """获取对话摘要（支持分层：L1/L2/L3）"""
        try:
            summary_key = f"conversation_summary:{user_id}:{conversation_id}:{layer}"
            summary = self.redis_conn.get(summary_key)
            
            if summary:
                logger.debug(f"Retrieved {layer} summary for {user_id}:{conversation_id}")
                if isinstance(summary, bytes):
                    return summary.decode('utf-8')
                return str(summary)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation summary for {user_id}:{conversation_id} ({layer}): {e}")
            return None
    
    async def set_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary: str,
        layer: str = "L1",
        ttl: int = 86400 * 30
    ) -> bool:
        """存储对话摘要（支持分层：L1/L2/L3）"""
        try:
            summary_key = f"conversation_summary:{user_id}:{conversation_id}:{layer}"
            result = self.redis_conn.setex(summary_key, ttl, summary)
            
            if result:
                logger.info(f"Stored {layer} summary for {user_id}:{conversation_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to store conversation summary for {user_id}:{conversation_id} ({layer}): {e}")
            return False


# 全局实例
redis_manager = RedisManager()

