"""
短期记忆模块
负责管理对话历史、压缩和最近的上下文
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from collections import deque
import threading
import uuid

from utils.logger import app_logger, log_execution_time
from memory.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期记忆管理器"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.redis_manager = redis_manager
        
        # 短期记忆配置
        self.max_tokens = 3000  # 3k token阈值
        self.warning_tokens = 2500  # 警告阈值
        self.max_recent_turns = 3  # 保留最近3轮对话
        
        # 异步压缩配置
        self.compression_queue = deque()  # 压缩任务队列
        self.compression_lock = threading.Lock()  # 队列锁
        self.max_concurrent_compressions = 3  # 最大并发压缩数
        self.max_queue_size = 100  # 最大队列大小
        self.active_compressions = 0  # 当前活跃压缩数
        
        # 递增总结配置
        self.summary_layers = {
            'L1': {'max_turns': 2, 'description': '单轮对话摘要'},  # 最近2轮
            'L2': {'max_turns': 5, 'description': '多轮对话摘要'},  # 最近5轮
            'L3': {'max_turns': 10, 'description': '主题聚类摘要'}   # 最近10轮
        }
        
        # 异步压缩处理器将在第一次使用时启动
        self._compression_processor_started = False
        
        app_logger.info(f"ShortTermMemory initialized - enabled: {enabled}")
    
    async def _ensure_compression_processor_started(self) -> None:
        """确保压缩处理器已启动"""
        if not self._compression_processor_started and self.enabled:
            self._compression_processor_started = True
            asyncio.create_task(self._compression_processor())
            app_logger.info("Compression processor started")
    
    @log_execution_time(log_args=True)
    async def get_recent_context(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """获取最近的对话上下文：Redis优先，DB回退"""
        if not self.enabled:
            app_logger.info(f"🔍 [SHORT-TERM] Memory disabled for {user_id}:{conversation_id}")
            return {
                "context": "",
                "metadata": {
                    "enabled": False,
                    "reason": "Short-term memory disabled"
                }
            }
        
        try:
            app_logger.info(f"🔍 [SHORT-TERM] Getting context for {user_id}:{conversation_id} (limit={limit})")
            
            # 1. 优先从Redis获取短期记忆
            redis_context = await self._get_from_redis(user_id, conversation_id, limit)
            conversations = await self.redis_manager.get_recent_conversations(user_id, conversation_id, limit)
            
            if redis_context:
                # Redis中有数据，直接返回
                app_logger.info(f"📝 [SHORT-TERM] Retrieved from Redis for {user_id}:{conversation_id}")
                app_logger.info(f"📄 [SHORT-TERM] Context content: {redis_context[:200]}...")
                return {
                    "context": redis_context,
                    "metadata": {
                        "enabled": True,
                        "source": "redis",
                        "limit": limit,
                        "conversations": conversations  # 包含原始对话数据用于意图识别
                    }
                }
            
            # 2. Redis中没有数据，从数据库获取并存储到Redis
            from database import conversation_repo
            
            recent_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=limit
            )
            
            app_logger.info(f"📊 [SHORT-TERM] Retrieved {len(recent_messages)} messages from database for {user_id}:{conversation_id}")
            
            if not recent_messages:
                app_logger.info(f"📭 [SHORT-TERM] No messages found for {user_id}:{conversation_id}")
                return {
                    "context": "",
                    "metadata": {
                        "enabled": True,
                        "source": "database",
                        "recent_turns": 0,
                        "limit": limit,
                        "conversations": []  # 空列表用于意图识别
                    }
                }
            
            # 3. 检查是否需要压缩
            total_tokens = self._count_tokens_for_messages(recent_messages)
            app_logger.info(f"🔢 [SHORT-TERM] Token count: {total_tokens}/{self.max_tokens} for {user_id}:{conversation_id}")
            
            if total_tokens > self.max_tokens:
                # 超过3k token，需要压缩
                app_logger.info(f"🗜️ [SHORT-TERM] Compressing messages for {user_id}:{conversation_id}")
                await self._compress_and_store(user_id, conversation_id, recent_messages)
                
                # 重新从Redis获取压缩后的数据
                redis_context = await self._get_from_redis(user_id, conversation_id, limit)
                conversations = await self.redis_manager.get_recent_conversations(user_id, conversation_id, limit)
                app_logger.info(f"📄 [SHORT-TERM] Compressed context: {redis_context[:200]}...")
                return {
                    "context": redis_context or "",
                    "metadata": {
                        "enabled": True,
                        "source": "redis_compressed",
                        "recent_turns": len(recent_messages),
                        "compressed": True,
                        "limit": limit,
                        "conversations": conversations  # 包含原始对话数据用于意图识别
                    }
                }
            else:
                # 未超过3k token，直接存储到Redis
                app_logger.info(f"💾 [SHORT-TERM] Storing {len(recent_messages)} messages to Redis for {user_id}:{conversation_id}")
                for i, msg in enumerate(recent_messages):
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                    app_logger.info(f"💬 [SHORT-TERM] Message {i+1}: User: {msg.get('user_message', '')[:50]}... | AI: {msg.get('ai_response', '')[:50]}...")
                
                # 格式化并返回
                context = self._format_recent_messages(recent_messages)
                conversations = await self.redis_manager.get_recent_conversations(user_id, conversation_id, limit)
                app_logger.info(f"📄 [SHORT-TERM] Formatted context: {context[:200]}...")
                return {
                    "context": context,
                    "metadata": {
                        "enabled": True,
                        "conversations": conversations,  # 包含原始对话数据用于意图识别
                        "source": "database_to_redis",
                        "recent_turns": len(recent_messages),
                        "compressed": False,
                        "limit": limit
                    }
                }
            
        except Exception as e:
            app_logger.error(f"Failed to get recent context: {e}")
            return {
                "context": "",
                "metadata": {
                    "enabled": True,
                    "error": str(e)
                }
            }
    
    def _count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息的token数量"""
        total_text = ""
        for message in messages:
            total_text += message.get("content", "")
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    def _format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
        """格式化最近的消息"""
        if not messages:
            return ""
        
        formatted = []
        for msg in messages:
            user_msg = msg.get('user_message', '')
            ai_response = msg.get('ai_response', '')
            if user_msg and ai_response:
                formatted.append(f"User: {user_msg}")
                formatted.append(f"Assistant: {ai_response}")
                formatted.append("")  # 空行分隔
        
        return "\n".join(formatted)
    
    def _format_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """格式化对话历史（去重处理）"""
        if not conversations:
            return ""
        
        # 去重处理：使用消息内容作为key
        seen_messages = set()
        unique_conversations = []
        
        for conv in conversations:
            message = conv.get("message", "")
            response = conv.get("response", "")
            
            # 创建消息的唯一标识
            message_key = f"{message}|{response}"
            
            if message_key not in seen_messages:
                seen_messages.add(message_key)
                unique_conversations.append(conv)
        
        app_logger.info(f"📊 [SHORT-TERM] Filtered {len(conversations)} -> {len(unique_conversations)} unique conversations")
        
        formatted = []
        for conv in unique_conversations:
            timestamp = conv.get("timestamp", "")
            message = conv.get("message", "")
            response = conv.get("response", "")
            
            formatted.append(f"[{timestamp}] 用户: {message}")
            formatted.append(f"[{timestamp}] 助手: {response}")
        
        return "\n".join(formatted)
    
    async def store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """存储单轮对话到短期记忆"""
        if not self.enabled:
            return False
        
        try:
            await self.redis_manager.store_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                response=response,
                metadata=metadata or {}
            )
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to store conversation: {e}")
            return False
    
    async def smart_store_conversation(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """智能存储对话：使用异步压缩和递增总结"""
        if not self.enabled:
            app_logger.info(f"🔍 [SHORT-TERM] Memory disabled, skipping storage for {user_id}:{conversation_id}")
            return False
        
        try:
            app_logger.info(f"💾 [SHORT-TERM] Smart storing conversation for {user_id}:{conversation_id}")
            app_logger.info(f"💬 [SHORT-TERM] New message: User: {message[:100]}...")
            app_logger.info(f"🤖 [SHORT-TERM] New response: AI: {response[:100]}...")
            
            # 确保压缩处理器已启动
            await self._ensure_compression_processor_started()
            
            # 先直接存储当前对话
            await self.redis_manager.store_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                response=response,
                metadata=metadata or {}
            )
            app_logger.info(f"✅ [SHORT-TERM] Stored conversation to Redis for {user_id}:{conversation_id}")
            
            # 获取当前对话的所有消息
            from database import conversation_repo
            all_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            # 计算总token数
            total_tokens = self._count_tokens_for_messages(all_messages)
            app_logger.info(f"🔢 [SHORT-TERM] Total messages: {len(all_messages)}, Total tokens: {total_tokens}/{self.max_tokens}")
            
            # 检查是否需要异步压缩
            if total_tokens > self.warning_tokens:
                priority = 'high' if total_tokens > self.max_tokens else 'normal'
                app_logger.info(f"⚠️ [SHORT-TERM] Token limit exceeded, queuing compression task with priority: {priority}")
                # 添加到异步压缩队列
                await self._queue_compression_task(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    priority=priority
                )
            else:
                app_logger.info(f"✅ [SHORT-TERM] Token count within limits, no compression needed")
            
            return True
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to smart store conversation: {e}")
            return False
    
    async def clear_user_data(self, user_id: str) -> bool:
        """清理用户的短期记忆数据"""
        if not self.enabled:
            return True
        
        try:
            await self.redis_manager.clear_user_data(user_id)
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to clear user data: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Short-term memory is disabled",
                "components": {
                    "redis_manager": "disabled"
                }
            }
        
        try:
            # 检查Redis连接
            redis_health = await self.redis_manager.health_check()
            
            # 获取压缩队列状态
            with self.compression_lock:
                queue_size = len(self.compression_queue)
                queue_tasks = [
                    {
                        'id': task.get('id', 'unknown'),
                        'user_id': task.get('user_id', 'unknown'),
                        'conversation_id': task.get('conversation_id', 'unknown'),
                        'priority': task.get('priority', 'normal'),
                        'status': task.get('status', 'queued'),
                        'created_at': task.get('created_at', 'unknown')
                    }
                    for task in list(self.compression_queue)
                ]
            
            return {
                "status": "ok",
                "message": "Short-term memory is healthy",
                "components": {
                    "redis_manager": redis_health["status"],
                    "async_compression": "enabled",
                    "incremental_summary": "enabled"
                },
                "config": {
                    "max_tokens": self.max_tokens,
                    "warning_tokens": self.warning_tokens,
                    "max_recent_turns": self.max_recent_turns,
                    "max_concurrent_compressions": self.max_concurrent_compressions,
                    "max_queue_size": self.max_queue_size,
                    "enabled": self.enabled
                },
                "compression_status": {
                    "queue_size": queue_size,
                    "active_compressions": self.active_compressions,
                    "queued_tasks": queue_tasks
                },
                "summary_layers": {
                    layer: {
                        "max_turns": config["max_turns"],
                        "description": config["description"]
                    }
                    for layer, config in self.summary_layers.items()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Short-term memory health check failed: {e}",
                "components": {
                    "redis_manager": "error"
                }
            }


    async def _get_summarized_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> str:
        """获取更早对话的summarized信息"""
        try:
            # 从Redis获取当前对话的summarized信息
            summary_key = f"conversation_summary:{user_id}:{conversation_id}"
            summary = self.redis_manager.redis_conn.get(summary_key)
            
            if summary:
                # Redis返回的数据可能是字符串或字节，需要处理
                if isinstance(summary, bytes):
                    return summary.decode('utf-8')
                return str(summary)
            
            return ""
            
        except Exception as e:
            app_logger.error(f"Failed to get summarized context: {e}")
            return ""
    
    async def store_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary: str
    ) -> bool:
        """存储对话摘要到Redis"""
        try:
            summary_key = f"conversation_summary:{user_id}:{conversation_id}"
            self.redis_manager.redis_conn.set(
                summary_key,
                summary,
                ex=86400 * 30  # 30天过期
            )
            app_logger.info(f"Stored conversation summary for {user_id}:{conversation_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to store conversation summary: {e}")
            return False
    
    async def generate_and_store_summary(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """生成并存储对话摘要"""
        try:
            if len(messages) < 6:  # 少于3轮对话不需要摘要
                return False
            
            # 使用AI生成摘要
            from services.ai_service import ai_service
            
            # 构建对话文本
            conversation_text = ""
            for msg in messages[:-4]:  # 排除最近2轮对话
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    conversation_text += f"用户: {content}\n"
                elif role == 'assistant':
                    conversation_text += f"助手: {content}\n"
            
            if not conversation_text.strip():
                return False
            
            # 生成摘要
            summary_prompt = f"""请为以下对话生成一个简洁的摘要，保留关键信息和上下文：

{conversation_text}

摘要要求：
1. 用2-3句话概括对话的主要内容
2. 保留重要的用户需求和AI的回答要点
3. 使用中文，语言简洁明了

摘要："""
            
            summary = await ai_service.generate_response(
                user_message=summary_prompt,
                intent="normal",
                full_context=""
            )
            
            if summary and len(summary.strip()) > 10:
                return await self.store_conversation_summary(user_id, conversation_id, summary.strip())
            
            return False
            
        except Exception as e:
            app_logger.error(f"Failed to generate and store summary: {e}")
            return False
    
    def _count_tokens_for_messages(self, messages: List[Dict[str, Any]]) -> int:
        """计算消息列表的token数量"""
        total_text = ""
        for msg in messages:
            total_text += msg.get('user_message', '') + " " + msg.get('ai_response', '')
        
        # 简单估算：中文1个字符≈1.5个token，英文1个词≈1个token
        chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in total_text.split() if w.isalpha()])
        
        return int(chinese_chars * 1.5 + english_words)
    
    async def _compress_and_store(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """压缩并存储对话"""
        try:
            # 保留最近3轮对话
            recent_messages = messages[-self.max_recent_turns:] if len(messages) > self.max_recent_turns else messages
            old_messages = messages[:-self.max_recent_turns] if len(messages) > self.max_recent_turns else []
            
            if not old_messages:
                # 没有旧消息需要压缩，直接存储最近对话
                for msg in recent_messages:
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                return True
            
            # 生成旧消息的摘要
            summary = await self._generate_summary_for_messages(old_messages)
            
            if summary:
                # 存储摘要到Redis
                await self.store_conversation_summary(user_id, conversation_id, summary)
                
                # 存储最近3轮对话
                for msg in recent_messages:
                    await self.redis_manager.store_conversation(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message=msg.get('user_message', ''),
                        response=msg.get('ai_response', ''),
                        metadata={}
                    )
                
                app_logger.info(f"Compressed and stored conversation for {user_id}:{conversation_id}")
                return True
            
            return False
            
        except Exception as e:
            app_logger.error(f"Failed to compress and store: {e}")
            return False
    
    async def _generate_summary_for_messages(self, messages: List[Dict[str, Any]]) -> str:
        """为消息列表生成摘要"""
        try:
            if not messages:
                return ""
            
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                conversation_text += f"用户: {msg.get('user_message', '')}\n"
                conversation_text += f"助手: {msg.get('ai_response', '')}\n"
            
            if not conversation_text.strip():
                return ""
            
            # 使用AI生成摘要
            from services.ai_service import ai_service
            
            summary_prompt = f"""请为以下对话生成一个简洁的摘要，保留关键信息和上下文：

{conversation_text}

摘要要求：
1. 用2-3句话概括对话的主要内容
2. 保留重要的用户需求和AI的回答要点
3. 使用中文，语言简洁明了

摘要："""
            
            summary = await ai_service.generate_response(
                user_message=summary_prompt,
                intent="normal",
                full_context=""
            )
            return summary.strip() if summary else ""
            
        except Exception as e:
            app_logger.error(f"Failed to generate summary for messages: {e}")
            return ""
    
    async def _get_from_redis(self, user_id: str, conversation_id: str, limit: int = 10) -> str:
        """从Redis获取短期记忆上下文（支持分层摘要）"""
        try:
            app_logger.info(f"🔍 [SHORT-TERM] Getting context from Redis for {user_id}:{conversation_id}")
            
            # 获取Redis中的对话数据
            conversations = await self.redis_manager.get_recent_conversations(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=limit
            )
            app_logger.info(f"📊 [SHORT-TERM] Retrieved {len(conversations)} conversations from Redis")
            
            # 获取分层摘要
            layer_summaries = await self._get_layer_summaries(user_id, conversation_id)
            app_logger.info(f"📋 [SHORT-TERM] Layer summaries: {list(layer_summaries.keys())}")
            
            # 打印每层摘要内容
            for layer, summary in layer_summaries.items():
                app_logger.info(f"📄 [SHORT-TERM] {layer} Summary: {summary[:100]}...")
            
            # 组合上下文
            context_parts = []
            
            # 添加分层摘要（从最旧到最新）
            if layer_summaries.get('L3'):
                context_parts.append(f"Earlier conversation summary (L3):\n{layer_summaries['L3']}")
                app_logger.info(f"📝 [SHORT-TERM] Added L3 summary to context")
            
            if layer_summaries.get('L2'):
                context_parts.append(f"Recent conversation summary (L2):\n{layer_summaries['L2']}")
                app_logger.info(f"📝 [SHORT-TERM] Added L2 summary to context")
            
            if layer_summaries.get('L1'):
                context_parts.append(f"Latest conversation summary (L1):\n{layer_summaries['L1']}")
                app_logger.info(f"📝 [SHORT-TERM] Added L1 summary to context")
            
            # 添加最近的对话
            if conversations:
                recent_context = self._format_conversations(conversations)
                context_parts.append(f"Current conversation:\n{recent_context}")
                app_logger.info(f"📝 [SHORT-TERM] Added {len(conversations)} recent conversations to context")
            
            final_context = "\n\n".join(context_parts)
            app_logger.info(f"📄 [SHORT-TERM] Final context length: {len(final_context)} characters")
            
            return final_context
            
        except Exception as e:
            app_logger.error(f"❌ [SHORT-TERM] Failed to get from Redis: {e}")
            return ""

    async def _get_layer_summaries(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, str]:
        """获取分层摘要"""
        try:
            summaries = {}
            for layer in ['L1', 'L2', 'L3']:
                summary_key = f"conversation_summary:{user_id}:{conversation_id}:{layer}"
                # 使用异步方式执行Redis操作
                summary = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_manager.redis_conn.get, summary_key
                )
                if summary:
                    if isinstance(summary, bytes):
                        summaries[layer] = summary.decode('utf-8')
                    else:
                        summaries[layer] = str(summary)
            return summaries
        except Exception as e:
            app_logger.error(f"Failed to get layer summaries: {e}")
            return {}

    async def _queue_compression_task(
        self,
        user_id: str,
        conversation_id: str,
        priority: str = 'normal'
    ) -> None:
        """将压缩任务添加到队列"""
        try:
            task = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'conversation_id': conversation_id,
                'priority': priority,
                'created_at': datetime.now().isoformat(),
                'status': 'queued'
            }
            
            with self.compression_lock:
                # 检查队列大小限制
                if len(self.compression_queue) >= self.max_queue_size:
                    # 队列已满，丢弃最老的任务
                    if priority == 'high':
                        # 高优先级任务，丢弃最老的普通优先级任务
                        old_task = None
                        for i, queued_task in enumerate(self.compression_queue):
                            if queued_task.get('priority') == 'normal':
                                old_task = self.compression_queue.pop(i)
                                break
                        if old_task:
                            app_logger.warning(f"Queue full, discarded normal priority task {old_task.get('id', 'unknown')}")
                        else:
                            app_logger.warning(f"Queue full, cannot add high priority task {task['id']}")
                            return
                    else:
                        # 普通优先级任务，丢弃最老的任务
                        old_task = self.compression_queue.popleft()
                        app_logger.warning(f"Queue full, discarded task {old_task.get('id', 'unknown')}")
                
                # 添加新任务
                if priority == 'high':
                    # 高优先级任务插入到队列前面
                    self.compression_queue.appendleft(task)
                else:
                    # 普通优先级任务插入到队列后面
                    self.compression_queue.append(task)
            
            app_logger.info(f"Queued compression task for {user_id}:{conversation_id} with priority {priority}")
            
        except Exception as e:
            app_logger.error(f"Failed to queue compression task: {e}")

    async def _compression_processor(self) -> None:
        """异步压缩处理器"""
        while self.enabled:
            try:
                # 检查是否有活跃压缩任务和队列任务
                if self.active_compressions < self.max_concurrent_compressions and self.compression_queue:
                    # 获取下一个任务
                    with self.compression_lock:
                        if not self.compression_queue:
                            continue
                        task = self.compression_queue.popleft()
                    
                    # 更新任务状态
                    task['status'] = 'processing'
                    
                    # 线程安全地增加活跃压缩计数
                    with self.compression_lock:
                        self.active_compressions += 1
                    
                    # 异步处理压缩任务
                    asyncio.create_task(self._process_compression_task(task))
                
                # 等待一段时间再检查
                await asyncio.sleep(1)
                
            except Exception as e:
                app_logger.error(f"Compression processor error: {e}")
                await asyncio.sleep(5)

    async def _process_compression_task(self, task: Dict[str, Any]) -> None:
        """处理单个压缩任务"""
        try:
            user_id = task['user_id']
            conversation_id = task['conversation_id']
            task_id = task['id']
            
            app_logger.info(f"Processing compression task {task_id} for {user_id}:{conversation_id}")
            
            # 获取对话消息
            from database import conversation_repo
            all_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            if not all_messages:
                return
            
            # 执行递增总结压缩
            await self._incremental_compression(user_id, conversation_id, all_messages)
            
            app_logger.info(f"Completed compression task {task_id} for {user_id}:{conversation_id}")
            
        except Exception as e:
            app_logger.error(f"Failed to process compression task {task.get('id', 'unknown')}: {e}")
        finally:
            # 线程安全地减少活跃压缩计数
            with self.compression_lock:
                self.active_compressions = max(0, self.active_compressions - 1)

    async def _incremental_compression(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """递增总结压缩"""
        try:
            total_messages = len(messages)
            if total_messages < 6:  # 少于3轮对话不需要压缩
                return True
            
            # 获取现有的摘要层
            existing_summaries = await self._get_existing_summaries(user_id, conversation_id)
            
            # 分层处理 - 按层级从大到小处理
            new_summaries = {}
            messages_to_keep = []
            
            # 确定需要保留的消息数量（取最大的层）
            max_keep_turns = max(
                self.summary_layers['L1']['max_turns'],
                self.summary_layers['L2']['max_turns'], 
                self.summary_layers['L3']['max_turns']
            )
            
            # 保留最近的消息
            if total_messages > max_keep_turns:
                messages_to_keep = messages[-max_keep_turns:]
                messages_to_summarize = messages[:-max_keep_turns]
            else:
                messages_to_keep = messages
                messages_to_summarize = []
            
            # 如果没有需要摘要的消息，直接返回
            if not messages_to_summarize:
                app_logger.info(f"No messages need summarization for {user_id}:{conversation_id}")
                return True
            
            # 根据消息数量决定生成哪些层的摘要
            if len(messages_to_summarize) >= 8:  # 足够生成L3摘要
                l3_summary = await self._generate_layer_summary(
                    'L3', messages_to_summarize, existing_summaries.get('L3')
                )
                if l3_summary:
                    new_summaries['L3'] = l3_summary
                
                # 生成L2摘要（从L3摘要中提取或重新生成）
                l2_summary = await self._generate_layer_summary(
                    'L2', messages_to_summarize[-5:], existing_summaries.get('L2')
                )
                if l2_summary:
                    new_summaries['L2'] = l2_summary
                    
            elif len(messages_to_summarize) >= 3:  # 足够生成L2摘要
                l2_summary = await self._generate_layer_summary(
                    'L2', messages_to_summarize, existing_summaries.get('L2')
                )
                if l2_summary:
                    new_summaries['L2'] = l2_summary
            
            # 总是生成L1摘要（如果有多余消息）
            if len(messages_to_summarize) >= 1:
                l1_summary = await self._generate_layer_summary(
                    'L1', messages_to_summarize[-2:], existing_summaries.get('L1')
                )
                if l1_summary:
                    new_summaries['L1'] = l1_summary
            
            # 存储新的摘要
            if new_summaries:
                await self._store_layer_summaries(user_id, conversation_id, new_summaries)
            
            # 清理Redis中的旧消息，只保留需要保留的消息
            await self._cleanup_old_messages(user_id, conversation_id, messages_to_keep)
            
            app_logger.info(f"Incremental compression completed for {user_id}:{conversation_id} - kept {len(messages_to_keep)} messages, generated {len(new_summaries)} summaries")
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to perform incremental compression: {e}")
            return False

    async def _get_existing_summaries(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, str]:
        """获取现有的摘要层"""
        try:
            summaries = {}
            for layer in ['L1', 'L2', 'L3']:
                summary_key = f"conversation_summary:{user_id}:{conversation_id}:{layer}"
                # 使用异步方式执行Redis操作
                summary = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_manager.redis_conn.get, summary_key
                )
                if summary:
                    if isinstance(summary, bytes):
                        summaries[layer] = summary.decode('utf-8')
                    else:
                        summaries[layer] = str(summary)
            return summaries
        except Exception as e:
            app_logger.error(f"Failed to get existing summaries: {e}")
            return {}

    async def _generate_layer_summary(
        self,
        layer: str,
        messages: List[Dict[str, Any]],
        existing_summary: Optional[str] = None
    ) -> Optional[str]:
        """生成指定层的摘要"""
        try:
            if not messages:
                return None
            
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                conversation_text += f"用户: {msg.get('user_message', '')}\n"
                conversation_text += f"助手: {msg.get('ai_response', '')}\n"
            
            if not conversation_text.strip():
                return None
            
            # 如果有现有摘要，进行递增更新
            if existing_summary:
                summary_prompt = f"""请基于现有摘要和新对话内容，生成更新的摘要：

现有摘要：
{existing_summary}

新对话内容：
{conversation_text}

要求：
1. 保留现有摘要中的重要信息
2. 整合新对话的关键内容
3. 保持摘要简洁明了（{self.summary_layers[layer]['description']}）
4. 使用中文

更新后的摘要："""
            else:
                summary_prompt = f"""请为以下对话生成摘要：

{conversation_text}

要求：
1. 用2-3句话概括对话的主要内容
2. 保留重要的用户需求和AI的回答要点
3. 使用中文，语言简洁明了
4. 这是{self.summary_layers[layer]['description']}

摘要："""
            
            # 使用AI生成摘要
            from services.ai_service import ai_service
            summary = await ai_service.generate_response(
                user_message=summary_prompt,
                intent="normal",
                full_context=""
            )
            
            return summary.strip() if summary else None
            
        except Exception as e:
            app_logger.error(f"Failed to generate {layer} summary: {e}")
            return None

    async def _store_layer_summaries(
        self,
        user_id: str,
        conversation_id: str,
        summaries: Dict[str, str]
    ) -> None:
        """存储分层摘要"""
        try:
            for layer, summary in summaries.items():
                if summary:
                    summary_key = f"conversation_summary:{user_id}:{conversation_id}:{layer}"
                    # 使用异步方式执行Redis操作
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.redis_manager.redis_conn.setex(
                            summary_key,
                            86400 * 30,  # 30天过期
                            summary
                        )
                    )
                    app_logger.info(f"Stored {layer} summary for {user_id}:{conversation_id}")
        except Exception as e:
            app_logger.error(f"Failed to store layer summaries: {e}")

    async def _cleanup_old_messages(
        self,
        user_id: str,
        conversation_id: str,
        keep_messages: List[Dict[str, Any]]
    ) -> None:
        """清理Redis中的旧消息"""
        try:
            # 获取Redis中的所有对话
            conversations = await self.redis_manager.get_recent_conversations(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=100
            )
            
            if not conversations:
                return
            
            # 获取需要保留的消息ID集合
            keep_message_ids = set()
            for msg in keep_messages:
                # 假设消息有ID字段，如果没有则使用内容hash
                msg_id = msg.get('id') or msg.get('message_id')
                if not msg_id:
                    # 使用内容生成唯一标识
                    content = f"{msg.get('user_message', '')}{msg.get('ai_response', '')}"
                    msg_id = str(hash(content))
                keep_message_ids.add(str(msg_id))
            
            # 清理Redis中不在保留列表中的消息
            deleted_count = 0
            for conv in conversations:
                conv_id = conv.get('id') or conv.get('message_id')
                if not conv_id:
                    content = f"{conv.get('message', '')}{conv.get('response', '')}"
                    conv_id = str(hash(content))
                
                if str(conv_id) not in keep_message_ids:
                    # 删除旧消息（这里需要根据Redis的具体键结构来实现）
                    # 暂时使用通用的清理方法
                    try:
                        # 假设Redis中的键格式为: conversation:{user_id}:{conversation_id}:{message_id}
                        message_key = f"conversation:{user_id}:{conversation_id}:{conv_id}"
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.redis_manager.redis_conn.delete, message_key
                        )
                        deleted_count += 1
                    except Exception as delete_error:
                        app_logger.warning(f"Failed to delete message {conv_id}: {delete_error}")
            
            app_logger.info(f"Cleanup completed for {user_id}:{conversation_id} - kept {len(keep_messages)} messages, deleted {deleted_count} old messages")
            
        except Exception as e:
            app_logger.error(f"Failed to cleanup old messages: {e}")

# 全局实例 - 默认启用
short_term_memory = ShortTermMemory(enabled=True)
