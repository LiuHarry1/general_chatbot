"""
简化的记忆系统
提供统一的长短期记忆管理接口
"""
from .memory_manager import MemoryManager
from .cache import CacheService
from .vector_store import VectorStoreService
from .embedding import EmbeddingService

# 创建默认实例
default_cache = CacheService()
default_vector_store = VectorStoreService()
default_embedding = EmbeddingService()
default_memory_manager = MemoryManager(
    cache=default_cache,
    vector_store=default_vector_store,
    embedding=default_embedding
)

__all__ = [
    'MemoryManager',
    'CacheService', 
    'VectorStoreService',
    'EmbeddingService',
    'default_memory_manager',
    'default_cache',
    'default_vector_store', 
    'default_embedding'
]
