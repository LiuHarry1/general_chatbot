"""
向量存储服务
简化的Qdrant向量数据库实现
"""
from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """简化的向量存储服务"""
    
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "chatbot_memory"):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self._create_collection_if_not_exists()
        logger.info(f"VectorStoreService initialized: {host}:{port}, collection: {collection_name}")

    def _create_collection_if_not_exists(self):
        """创建Qdrant集合（如果不存在）"""
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info(f"Qdrant collection '{self.collection_name}' created.")
            else:
                logger.info(f"Qdrant collection '{self.collection_name}' already exists.")
        except Exception as e:
            logger.error(f"Error creating Qdrant collection: {e}")

    async def add_document(self, document_id: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加文档到向量存储"""
        try:
            points = [
                PointStruct(
                    id=document_id,
                    vector=embedding,
                    payload={"content": content, **(metadata if metadata else {})}
                )
            ]
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            logger.debug(f"Document '{document_id}' added to vector store.")
            return True
        except Exception as e:
            logger.error(f"Error adding document '{document_id}' to vector store: {e}")
            return False

    async def search_documents(self, query_embedding: List[float], limit: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        try:
            query_filter = None
            if filter:
                must_conditions = []
                for key, value in filter.items():
                    must_conditions.append(models.FieldCondition(
                        key=key,
                        range=models.Range(gte=value, lte=value)
                    ))
                query_filter = models.Filter(must=must_conditions)

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit
            )
            
            results = []
            for hit in search_result:
                payload = hit.payload if hit.payload else {}
                results.append({
                    "id": hit.id,
                    "content": payload.get("content"),
                    "score": hit.score,
                    "metadata": {k: v for k, v in payload.items() if k != "content"}
                })
            logger.debug(f"Searched vector store with limit {limit}, found {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档"""
        try:
            point = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True,
                with_vectors=False
            )
            if point and point[0]:
                payload = point[0].payload if point[0].payload else {}
                return {
                    "id": point[0].id,
                    "content": payload.get("content"),
                    "metadata": {k: v for k, v in payload.items() if k != "content"}
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving document '{document_id}' from vector store: {e}")
            return None

    async def delete_document(self, document_id: str) -> bool:
        """从向量存储删除文档"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[document_id])
            )
            logger.debug(f"Document '{document_id}' deleted from vector store.")
            return True
        except Exception as e:
            logger.error(f"Error deleting document '{document_id}' from vector store: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health = self.client.health_check()
            return {"status": "ok", "message": f"Qdrant is reachable, version: {health.version}"}
        except Exception as e:
            return {"status": "error", "message": f"Qdrant connection failed: {e}"}
