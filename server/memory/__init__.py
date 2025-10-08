"""
现代化记忆系统
提供统一的长短期记忆管理接口
"""
# 主要接口 - 统一记忆管理器
from .unified_memory import unified_memory_manager

# 子模块接口 - 用于直接访问特定功能
from .short_term_memory import short_term_memory
from .long_term_memory import long_term_memory

# 新的重构模块 - 可选直接访问
from .memory_formatter import memory_formatter
from .memory_compression import memory_compressor
from .summary_generator import summary_generator

# 延迟导入以避免循环依赖
def get_unified_memory_manager():
    """获取统一记忆管理器实例"""
    return unified_memory_manager

def get_short_term_memory():
    """获取短期记忆管理器实例"""
    return short_term_memory

def get_long_term_memory():
    """获取长期记忆管理器实例"""
    return long_term_memory


def get_redis_manager():
    from .redis_manager import redis_manager
    return redis_manager

def get_qdrant_manager():
    from .qdrant_manager import qdrant_manager
    return qdrant_manager

def get_embedding_service():
    from .embedding import EmbeddingService
    return EmbeddingService

def get_profile_service():
    from .profile_service import profile_service
    return profile_service

def get_semantic_search_service():
    from .semantic_search import semantic_search_service
    return semantic_search_service


def get_importance_calculator():
    from .importance_calculator import importance_calculator
    return importance_calculator

def get_memory_formatter():
    """获取内存格式化器实例"""
    return memory_formatter

def get_memory_compressor():
    """获取内存压缩器实例"""
    return memory_compressor

def get_summary_generator():
    """获取摘要生成器实例"""
    return summary_generator

# 创建默认嵌入服务实例
default_embedding = get_embedding_service()()

# 主要导出接口
__all__ = [
    # 主要接口
    'unified_memory_manager',
    'get_unified_memory_manager',
    
    # 子模块接口
    'short_term_memory',
    'long_term_memory', 
    'get_short_term_memory',
    'get_long_term_memory',
    
    # 重构后的新模块
    'memory_formatter',
    'memory_compressor',
    'summary_generator',
    'get_memory_formatter',
    'get_memory_compressor',
    'get_summary_generator',
    
    # 其他服务
    'get_redis_manager',
    'get_qdrant_manager',
    'get_embedding_service',
    'default_embedding',
    'get_profile_service',
    'get_semantic_search_service',
    'get_importance_calculator'
]
