"""
嵌入服务
简化的通义千问嵌入实现
"""
import httpx
from typing import List, Dict, Any
import logging

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """简化的嵌入服务"""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-v1"):
        self.api_key = api_key or settings.dashscope_api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info(f"EmbeddingService initialized with model: {model}")

    async def embed_text(self, text: str) -> List[float]:
        """将文本转换为嵌入向量"""
        return (await self.embed_texts([text]))[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为嵌入向量"""
        if not self.api_key:
            logger.error("Dashscope API key is not set for embedding service.")
            return [[] for _ in texts]

        payload = {
            "model": self.model,
            "input": {
                "texts": texts
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                embeddings = []
                for record in data.get("output", {}).get("embeddings", []):
                    embeddings.append(record.get("embedding", []))
                
                if len(embeddings) != len(texts):
                    logger.warning(f"Mismatch in number of embeddings returned. Expected {len(texts)}, got {len(embeddings)}")
                    while len(embeddings) < len(texts):
                        embeddings.append([])
                
                logger.debug(f"Successfully embedded {len(texts)} texts.")
                return embeddings
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error embedding texts: {e.response.status_code} - {e.response.text}")
            return [[] for _ in texts]
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            return [[] for _ in texts]
            
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            test_text = ["hello"]
            embeddings = await self.embed_texts(test_text)
            if embeddings and len(embeddings[0]) > 0:
                return {"status": "ok", "message": "Embedding service is reachable and functional"}
            else:
                return {"status": "error", "message": "Embedding service returned empty embedding"}
        except Exception as e:
            return {"status": "error", "message": f"Embedding service failed: {e}"}
