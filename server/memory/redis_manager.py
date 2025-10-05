"""
Redis Cache Manager
Modern cache and user profile storage implementation
"""
import json
import redis
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import logging

from config import settings

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
        """存储单轮对话"""
        try:
            conversation_key = f"conversation:{user_id}:{conversation_id}"
            timestamp = datetime.now().isoformat()
            
            conversation_data = {
                "message": message,
                "response": response,
                "timestamp": timestamp,
                "metadata": json.dumps(metadata or {}, ensure_ascii=False)
            }
            
            # 存储对话数据
            self.redis_conn.hset(
                conversation_key,
                mapping=conversation_data
            )
            
            # 设置过期时间（7天）
            self.redis_conn.expire(conversation_key, 7 * 24 * 3600)
            
            # 添加到用户对话列表
            user_conversations_key = f"user_conversations:{user_id}"
            self.redis_conn.lpush(user_conversations_key, conversation_id)
            self.redis_conn.expire(user_conversations_key, 7 * 24 * 3600)
            
            logger.info(f"Stored conversation for user {user_id}")
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
        """获取最近的对话（排除当前对话）"""
        try:
            conversations = []
            user_conversations_key = f"user_conversations:{user_id}"
            
            # 获取更多的对话ID列表，以便在排除当前对话后仍有足够的数量
            max_fetch = limit * 2  # 获取更多，确保排除当前对话后还有足够的数量
            all_conversation_ids = self.redis_conn.lrange(
                user_conversations_key, 0, max_fetch - 1
            )
            
            # 排除当前对话ID，并限制返回数量
            filtered_ids = []
            for conv_id in all_conversation_ids:
                # 处理可能的字节或字符串类型
                try:
                    if isinstance(conv_id, bytes):
                        conv_id_str = conv_id.decode('utf-8')
                    else:
                        conv_id_str = str(conv_id)
                    
                    if conv_id_str != conversation_id:
                        filtered_ids.append(conv_id_str)
                except Exception as e:
                    logger.warning(f"Failed to process conversation ID: {conv_id}, error: {e}")
                    continue
            
            filtered_ids = filtered_ids[:limit]
            
            for conv_id in filtered_ids:
                conversation_key = f"conversation:{user_id}:{conv_id}"
                
                # 获取对话数据
                conv_data = self.redis_conn.hgetall(conversation_key)
                if conv_data:
                    # 解码Redis返回的字节数据
                    decoded_data = {}
                    for k, v in conv_data.items():
                        if isinstance(k, bytes):
                            key = k.decode('utf-8')
                        else:
                            key = str(k)
                        
                        if isinstance(v, bytes):
                            value = v.decode('utf-8')
                        else:
                            value = str(v)
                        
                        decoded_data[key] = value
                    
                    conversations.append({
                        "conversation_id": conv_id,
                        "message": decoded_data.get("message", ""),
                        "response": decoded_data.get("response", ""),
                        "timestamp": decoded_data.get("timestamp", ""),
                        "metadata": decoded_data.get("metadata", "{}")
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get recent conversations: {e}")
            return []


# 全局实例
redis_manager = RedisManager()

