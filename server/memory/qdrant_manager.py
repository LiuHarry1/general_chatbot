"""
Qdrant向量数据库管理器
现代化的向量存储和语义搜索实现
"""
import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Qdrant向量数据库管理器"""
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.host = host
        self.port = port
        
        # 集合配置
        self.collections = {
            "semantic_memory": {
                "name": "semantic_memory",
                "vector_size": 1536,
                "distance": Distance.COSINE
            },
            "knowledge_graph": {
                "name": "knowledge_graph", 
                "vector_size": 1536,
                "distance": Distance.COSINE
            },
            "user_profiles": {
                "name": "user_profiles",
                "vector_size": 1536, 
                "distance": Distance.COSINE
            }
        }
        
        self._initialize_collections()
        logger.info(f"QdrantManager initialized: {host}:{port}")
    
    def _initialize_collections(self):
        """初始化所有集合"""
        try:
            existing_collections = {c.name for c in self.client.get_collections().collections}
            
            for collection_name, config in self.collections.items():
                if collection_name not in existing_collections:
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=config["vector_size"],
                            distance=config["distance"]
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.info(f"Collection {collection_name} already exists")
                    
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
    
    async def add_semantic_memory(
        self, 
        content: str, 
        embedding: List[float], 
        user_id: str,
        conversation_id: str,
        importance_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加语义记忆到向量数据库"""
        try:
            document_id = str(uuid.uuid4())
            
            payload = {
                "content": content,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "importance_score": importance_score,
                "created_at": datetime.now().isoformat(),
                "memory_type": "semantic",
                **(metadata or {})
            }
            
            point = PointStruct(
                id=document_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name="semantic_memory",
                points=[point]
            )
            
            logger.info(f"Added semantic memory: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Error adding semantic memory: {e}")
            return ""
    
    async def search_semantic_memory(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """搜索语义记忆"""
        try:
            # 构建用户过滤条件
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
            
            search_result = self.client.search(
                collection_name="semantic_memory",
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score
            )
            
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "content": hit.payload.get("content", ""),
                    "score": hit.score,
                    "importance_score": hit.payload.get("importance_score", 0.0),
                    "created_at": hit.payload.get("created_at", ""),
                    "metadata": {k: v for k, v in hit.payload.items() 
                               if k not in ["content", "user_id", "conversation_id", "importance_score", "created_at", "memory_type"]}
                })
            
            logger.info(f"Found {len(results)} semantic memories for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching semantic memory: {e}")
            return []
    
    async def add_knowledge_entity(
        self,
        entity_name: str,
        entity_type: str,
        embedding: List[float],
        user_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加知识图谱实体"""
        try:
            entity_id = str(uuid.uuid4())
            
            payload = {
                "entity_name": entity_name,
                "entity_type": entity_type,
                "user_id": user_id,
                "properties": properties or {},
                "created_at": datetime.now().isoformat(),
                "memory_type": "knowledge_entity"
            }
            
            point = PointStruct(
                id=entity_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name="knowledge_graph",
                points=[point]
            )
            
            logger.info(f"Added knowledge entity: {entity_name}")
            return entity_id
            
        except Exception as e:
            logger.error(f"Error adding knowledge entity: {e}")
            return ""
    
    async def search_knowledge_entities(
        self,
        query_embedding: List[float],
        user_id: str,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索知识图谱实体"""
        try:
            must_conditions = [
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
            
            if entity_type:
                must_conditions.append(
                    FieldCondition(
                        key="entity_type",
                        match=MatchValue(value=entity_type)
                    )
                )
            
            query_filter = Filter(must=must_conditions)
            
            search_result = self.client.search(
                collection_name="knowledge_graph",
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit
            )
            
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "entity_name": hit.payload.get("entity_name", ""),
                    "entity_type": hit.payload.get("entity_type", ""),
                    "properties": hit.payload.get("properties", {}),
                    "score": hit.score,
                    "created_at": hit.payload.get("created_at", "")
                })
            
            logger.info(f"Found {len(results)} knowledge entities for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge entities: {e}")
            return []
    
    async def get_memory_by_id(self, memory_id: str, collection_name: str) -> Optional[Dict[str, Any]]:
        """根据ID获取记忆"""
        try:
            point = self.client.retrieve(
                collection_name=collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False
            )
            
            if point and point[0]:
                return {
                    "id": point[0].id,
                    "payload": point[0].payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None
    
    async def delete_memory(self, memory_id: str, collection_name: str) -> bool:
        """删除记忆"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=[memory_id])
            )
            logger.info(f"Deleted memory: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection stats for {collection_name}: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health = self.client.health_check()
            return {
                "status": "ok",
                "message": f"Qdrant is reachable, version: {health.version}",
                "host": self.host,
                "port": self.port
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Qdrant connection failed: {e}",
                "host": self.host,
                "port": self.port
            }


# 全局实例
qdrant_manager = QdrantManager()

