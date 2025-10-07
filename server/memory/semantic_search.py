"""
Semantic Search Service
Intelligent memory retrieval based on vector similarity
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from utils.logger import app_logger
from memory.qdrant_manager import qdrant_manager
from memory.redis_manager import redis_manager
from memory.embedding import EmbeddingService
from memory.importance_calculator import importance_calculator

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Semantic search service"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        
        # 搜索配置
        self.default_limit = 5
        self.min_similarity_score = 0.7
        self.max_search_results = 20
        
        # 搜索权重配置
        self.search_weights = {
            "recent": 0.3,      # 时间权重
            "importance": 0.4,  # 重要性权重
            "similarity": 0.3   # 相似度权重
        }
        
        app_logger.info("SemanticSearchService initialized")
    
    async def search_semantic_memories(
        self,
        query: str,
        user_id: str,
        limit: int = None,
        memory_types: List[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        搜索语义记忆
        
        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 返回结果数量限制
            memory_types: 记忆类型过滤
            time_range: 时间范围过滤
            min_importance: 最小重要性阈值
            
        Returns:
            搜索结果列表
        """
        try:
            if limit is None:
                limit = self.default_limit
            
            # 生成查询向量
            query_embedding = await self.embedding_service.embed_text(query)
            if not query_embedding:
                app_logger.error("Failed to generate query embedding")
                return []
            
            # 搜索语义记忆
            semantic_results = await qdrant_manager.search_semantic_memory(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit * 2,  # 获取更多结果用于排序
                min_score=self.min_similarity_score
            )
            
            # 搜索知识实体
            knowledge_results = await qdrant_manager.search_knowledge_entities(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit
            )
            
            # 合并和排序结果
            all_results = await self._merge_and_rank_results(
                semantic_results,
                knowledge_results,
                query,
                user_id,
                time_range,
                min_importance
            )
            
            # 限制返回数量
            final_results = all_results[:limit]
            
            app_logger.info(f"语义搜索完成: 查询='{query[:50]}...', 用户={user_id}, 结果数={len(final_results)}")
            return final_results
            
        except Exception as e:
            app_logger.error(f"语义搜索失败: {e}")
            return []
    
    async def _merge_and_rank_results(
        self,
        semantic_results: List[Dict[str, Any]],
        knowledge_results: List[Dict[str, Any]],
        query: str,
        user_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """合并和排序搜索结果"""
        try:
            all_results = []
            
            # 处理语义记忆结果
            for result in semantic_results:
                # 应用时间过滤
                if time_range:
                    created_at = datetime.fromisoformat(result.get("created_at", ""))
                    if not (time_range[0] <= created_at <= time_range[1]):
                        continue
                
                # 应用重要性过滤
                importance = result.get("importance_score", 0.0)
                if importance < min_importance:
                    continue
                
                # 计算综合评分
                score = await self._calculate_comprehensive_score(
                    result, query, user_id, "semantic"
                )
                
                result["comprehensive_score"] = score
                result["result_type"] = "semantic_memory"
                all_results.append(result)
            
            # 处理知识实体结果
            for result in knowledge_results:
                # 计算综合评分
                score = await self._calculate_comprehensive_score(
                    result, query, user_id, "knowledge"
                )
                
                result["comprehensive_score"] = score
                result["result_type"] = "knowledge_entity"
                all_results.append(result)
            
            # 去重：基于内容去重，保留评分最高的
            unique_results = {}
            for result in all_results:
                content = result.get("content", "")
                if content not in unique_results or result["comprehensive_score"] > unique_results[content]["comprehensive_score"]:
                    unique_results[content] = result
            
            # 按综合评分排序
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: x["comprehensive_score"], reverse=True)
            
            return final_results
            
        except Exception as e:
            app_logger.error(f"合并排序结果失败: {e}")
            return []
    
    async def _calculate_comprehensive_score(
        self,
        result: Dict[str, Any],
        query: str,
        user_id: str,
        result_type: str
    ) -> float:
        """计算综合评分"""
        try:
            score = 0.0
            
            # 相似度评分
            similarity_score = result.get("score", 0.0)
            score += similarity_score * self.search_weights["similarity"]
            
            # 重要性评分
            importance_score = result.get("importance_score", 0.0)
            score += importance_score * self.search_weights["importance"]
            
            # 时间评分（越新越好）
            created_at = result.get("created_at", "")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at)
                    days_ago = (datetime.now() - created_time).days
                    time_score = max(0.0, 1.0 - (days_ago / 365))  # 一年内线性衰减
                    score += time_score * self.search_weights["recent"]
                except:
                    pass
            
            # 访问频率加分
            access_count = result.get("access_count", 0)
            if access_count > 0:
                access_bonus = min(0.1, access_count * 0.01)
                score += access_bonus
            
            # 结果类型权重
            if result_type == "semantic_memory":
                score *= 1.0  # 语义记忆权重
            elif result_type == "knowledge_entity":
                score *= 0.8  # 知识实体权重稍低
            
            return min(score, 1.0)  # 确保不超过1.0
            
        except Exception as e:
            app_logger.error(f"计算综合评分失败: {e}")
            return 0.0
    
    
    async def get_memory_timeline(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户记忆时间线"""
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # 搜索时间范围内的记忆
            results = await self.search_semantic_memories(
                query="",  # 空查询获取所有记忆
                user_id=user_id,
                limit=limit,
                time_range=(start_time, end_time)
            )
            
            # 按时间排序
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return results
            
        except Exception as e:
            app_logger.error(f"获取记忆时间线失败: {e}")
            return []
    
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查Qdrant连接
            qdrant_health = await qdrant_manager.health_check()
            
            # 检查Redis连接
            redis_health = await redis_manager.health_check()
            
            # 检查嵌入服务
            embedding_health = await self.embedding_service.health_check()
            
            overall_status = "ok"
            if (qdrant_health["status"] != "ok" or 
                redis_health["status"] != "ok" or 
                embedding_health["status"] != "ok"):
                overall_status = "error"
            
            return {
                "status": overall_status,
                "qdrant": qdrant_health,
                "redis": redis_health,
                "embedding": embedding_health,
                "search_config": {
                    "default_limit": self.default_limit,
                    "min_similarity_score": self.min_similarity_score,
                    "search_weights": self.search_weights
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Semantic search health check failed: {e}"
            }


# 全局实例
semantic_search_service = SemanticSearchService()

