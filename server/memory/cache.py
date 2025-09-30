"""
缓存服务
简化的Redis缓存实现
"""
import json
import redis.asyncio as redis
from typing import Any, Optional, Dict
import logging

from config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """简化的缓存服务"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        logger.info(f"CacheService initialized: {host}:{port}/{db}")

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
            else:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except Exception as e:
            logger.error(f"Error getting from Redis for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """设置缓存值，带过期时间 (秒)"""
        try:
            await self.redis.set(key, value, ex=ttl)
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error setting to Redis for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            result = await self.redis.delete(key)
            logger.debug(f"Cache delete for key: {key}, result: {result}")
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting from Redis for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """清空所有缓存"""
        try:
            await self.redis.flushdb()
            logger.info("Redis cache cleared.")
            return True
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self.redis.ping()
            return {"status": "ok", "message": "Redis is reachable"}
        except Exception as e:
            return {"status": "error", "message": f"Redis connection failed: {e}"}
