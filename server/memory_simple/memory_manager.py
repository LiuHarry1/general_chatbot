"""
记忆管理器
统一管理长短期记忆的简化实现
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import httpx

from .cache import CacheService
from .vector_store import VectorStoreService
from .embedding import EmbeddingService
from config import settings

logger = logging.getLogger(__name__)


class MemoryManager:
    """简化的记忆管理器"""
    
    def __init__(self, cache: CacheService, vector_store: VectorStoreService, embedding: EmbeddingService):
        self.cache = cache
        self.vector_store = vector_store
        self.embedding = embedding
        self.api_key = settings.dashscope_api_key
        self.llm_model = settings.qwen_model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info("MemoryManager initialized with simplified architecture.")

    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """调用LLM生成响应"""
        if not self.api_key:
            logger.error("Dashscope API key is not set for LLM calls.")
            return "LLM API key not configured."

        messages = [
            {"role": "system", "content": "你是一个专业的AI助手，擅长从对话中提取用户偏好和构建用户档案。"},
            {"role": "user", "content": prompt}
        ]
        payload = {
            "model": self.llm_model,
            "input": {"messages": messages},
            "parameters": {
                "temperature": temperature,
                "result_format": "message"
            }
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            return f"LLM API error: {e.response.text}"
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"LLM call failed: {e}"

    async def store_conversation_summary(self, conversation_id: str, summary: str, metadata: Dict[str, Any]) -> str:
        """存储对话摘要到长期记忆"""
        try:
            summary_embedding = await self.embedding.embed_text(summary)
            if not summary_embedding:
                logger.error("Failed to generate embedding for conversation summary.")
                return ""
            
            import uuid
            document_id = str(uuid.uuid4())
            success = await self.vector_store.add_document(
                document_id=document_id,
                content=summary,
                embedding=summary_embedding,
                metadata={"type": "conversation_summary", "conversation_id": conversation_id, **metadata}
            )
            if success:
                logger.info(f"Conversation summary stored: {conversation_id}")
                return document_id
            return ""
        except Exception as e:
            logger.error(f"Error storing conversation summary: {e}")
            return ""

    async def search_relevant_context(self, query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索相关上下文"""
        try:
            query_embedding = await self.embedding.embed_text(query)
            if not query_embedding:
                logger.error("Failed to generate embedding for query.")
                return []
            
            results = await self.vector_store.search_documents(
                query_embedding=query_embedding,
                limit=limit
            )
            logger.info(f"Found {len(results)} relevant contexts for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error searching relevant context: {e}")
            return []

    async def store_user_identity(self, user_id: str, identity_info: Dict[str, Any]) -> bool:
        """存储用户身份信息到短期记忆"""
        try:
            key = f"user_identity:{user_id}"
            existing_identity_str = await self.cache.get(key)
            existing_identity = json.loads(existing_identity_str) if existing_identity_str else {}
            
            merged_identity = {**existing_identity, **identity_info}
            merged_identity['last_updated'] = datetime.now().isoformat()
            
            success = await self.cache.set(key, json.dumps(merged_identity), ttl=3600 * 24 * 7)
            if success:
                logger.info(f"User identity stored/updated for user: {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error storing user identity: {e}")
            return False

    async def get_user_identity(self, user_id: str) -> Dict[str, Any]:
        """获取用户身份信息"""
        try:
            key = f"user_identity:{user_id}"
            identity_str = await self.cache.get(key)
            if identity_str:
                logger.debug(f"User identity retrieved for user: {user_id}")
                return json.loads(identity_str)
            return {}
        except Exception as e:
            logger.error(f"Error getting user identity: {e}")
            return {}

    async def extract_identity_from_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """从消息中提取身份信息"""
        try:
            prompt = f"""
            请从以下用户消息中提取用户偏好、习惯、兴趣、身份信息等。
            如果消息中包含"我是"、"我叫"、"我的名字是"等，请提取姓名。
            如果包含"我今年"、"我的年龄是"等，请提取年龄。
            如果包含"我住在"、"我来自"等，请提取居住地。
            如果包含"我的职业是"、"我是一名"、"我是做"等，请提取职业。
            如果包含"我喜欢"、"我爱"、"我讨厌"、"我不喜欢"等，请提取偏好。
            如果包含"我的爱好是"、"我感兴趣"等，请提取兴趣。

            请以JSON格式返回提取到的信息，例如：
            {{
                "preferences": ["喜欢咖啡", "不喜欢甜饮料"],
                "identity": {{
                    "name": "刘浩",
                    "age": 25,
                    "job": "软件工程师",
                    "location": "北京"
                }},
                "interests": ["看电影", "科幻片", "动作片"],
                "communication_style": "友好、直接",
                "confidence": 0.9,
                "extracted_at": "{datetime.now().isoformat()}"
            }}
            如果未提取到任何信息，请返回空JSON对象 {{}}.
            用户消息: "{message}"
            """
            
            llm_response = await self._call_llm(prompt, temperature=0.3)
            extracted_data = json.loads(llm_response)
            
            if extracted_data:
                await self._update_user_profile(user_id, extracted_data)
                logger.info(f"Extracted preferences for user {user_id}: {extracted_data}")
            return extracted_data
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from LLM response: {llm_response}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting preferences from message: {e}")
            return {}

    async def _update_user_profile(self, user_id: str, new_data: Dict[str, Any]):
        """更新用户的长期档案"""
        profile = await self.get_user_identity(user_id)
        
        # 合并偏好
        if "preferences" in new_data and isinstance(new_data["preferences"], list):
            existing_preferences = profile.get("preferences", [])
            for p in new_data["preferences"]:
                if p not in existing_preferences:
                    existing_preferences.append(p)
            profile["preferences"] = existing_preferences
        
        # 合并身份信息
        if "identity" in new_data and isinstance(new_data["identity"], dict):
            existing_identity = profile.get("identity", {})
            existing_identity.update(new_data["identity"])
            profile["identity"] = existing_identity
        
        # 合并兴趣
        if "interests" in new_data and isinstance(new_data["interests"], list):
            existing_interests = profile.get("interests", [])
            for i in new_data["interests"]:
                if i not in existing_interests:
                    existing_interests.append(i)
            profile["interests"] = existing_interests
        
        # 更新沟通风格
        if "communication_style" in new_data and new_data["communication_style"]:
            profile["communication_style"] = new_data["communication_style"]
        
        profile["last_updated"] = datetime.now().isoformat()
        await self.store_user_identity(user_id, profile)
        logger.info(f"User profile for {user_id} updated: {profile}")

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户的完整档案"""
        return await self.get_user_identity(user_id)

    async def add_memory(self, user_id: str, memory_text: str, metadata: Dict[str, Any] = None) -> bool:
        """添加记忆到长期存储"""
        try:
            # 生成摘要
            summary_prompt = f"请为以下对话内容生成一个简洁的摘要（不超过100字）：\n\n{memory_text}"
            summary = await self._call_llm(summary_prompt, temperature=0.3)
            if not summary or summary.startswith("LLM"):
                summary = memory_text[:100] + "..."
            
            # 存储到向量数据库
            conversation_id = metadata.get("conversation_id", "default") if metadata else "default"
            success = await self.store_conversation_summary(
                conversation_id=conversation_id,
                summary=summary,
                metadata={"user_id": user_id, **(metadata or {})}
            )
            
            if success:
                logger.info(f"Memory added for user {user_id}: {summary[:50]}...")
            return bool(success)
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return False

    async def get_user_memories(self, user_id: str, limit: int = 10) -> List[str]:
        """获取用户的记忆列表"""
        try:
            # 使用用户ID作为查询来搜索相关记忆
            query = f"用户 {user_id} 的对话历史"
            memories = await self.search_relevant_context(query, user_id, limit=limit)
            
            # 提取记忆文本
            memory_texts = []
            for memory in memories:
                if memory.get("content"):
                    memory_texts.append(memory["content"])
            
            logger.info(f"Retrieved {len(memory_texts)} memories for user {user_id}")
            return memory_texts
        except Exception as e:
            logger.error(f"Error getting user memories: {e}")
            return []

    async def build_contextual_prompt(self, user_id: str, current_message: str) -> str:
        """根据用户档案和当前消息构建个性化的上下文提示词"""
        profile = await self.get_user_profile(user_id)
        if not profile:
            return ""

        context_parts = ["\n\n以下是关于用户的一些已知信息，请在对话中自然地利用这些信息，让用户感受到你认识他们："]

        if profile.get("identity"):
            identity = profile["identity"]
            if identity.get("name"):
                context_parts.append(f"- 姓名：{identity['name']}")
            if identity.get("age"):
                context_parts.append(f"- 年龄：{identity['age']}岁")
            if identity.get("location"):
                context_parts.append(f"- 居住地：{identity['location']}")
            if identity.get("job"):
                context_parts.append(f"- 职业：{identity['job']}")
        
        if profile.get("preferences"):
            context_parts.append(f"- 偏好：{', '.join(profile['preferences'])}")
        
        if profile.get("interests"):
            context_parts.append(f"- 兴趣：{', '.join(profile['interests'])}")
        
        if profile.get("communication_style"):
            context_parts.append(f"- 沟通风格：{profile['communication_style']}")
        
        context_parts.append("\n请在回答时，结合上述信息，提供更个性化和连贯的回复。")
        
        return "\n".join(context_parts)

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        cache_health = await self.cache.health_check()
        vector_store_health = await self.vector_store.health_check()
        embedding_health = await self.embedding.health_check()
        
        overall_status = "ok" if cache_health["status"] == "ok" and vector_store_health["status"] == "ok" and embedding_health["status"] == "ok" else "error"
        
        return {
            "status": overall_status,
            "cache": cache_health,
            "vector_store": vector_store_health,
            "embedding": embedding_health
        }
