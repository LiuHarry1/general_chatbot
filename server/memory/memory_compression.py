"""
记忆压缩器
负责异步压缩和递增总结
"""
import asyncio
import uuid
from typing import List, Dict, Any
from datetime import datetime
from collections import deque
import threading
import logging

from utils.logger import app_logger
from memory.redis_manager import redis_manager
from memory.summary_generator import summary_generator

logger = logging.getLogger(__name__)


class MemoryCompressor:
    """记忆压缩器 - 负责异步压缩和递增总结"""
    
    def __init__(self):
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
        
        # 压缩处理器启动标志
        self._processor_started = False
        
        app_logger.info("MemoryCompressor initialized")
    
    async def ensure_processor_started(self) -> None:
        """确保压缩处理器已启动"""
        if not self._processor_started:
            self._processor_started = True
            asyncio.create_task(self._compression_processor())
            app_logger.info("Compression processor started")
    
    async def queue_compression_task(
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
                            app_logger.warning(f"⚠️ [COMPRESS] Queue full, discarded normal priority task {old_task.get('id', 'unknown')}")
                        else:
                            app_logger.warning(f"⚠️ [COMPRESS] Queue full, cannot add high priority task {task['id']}")
                            return
                    else:
                        # 普通优先级任务，丢弃最老的任务
                        old_task = self.compression_queue.popleft()
                        app_logger.warning(f"⚠️ [COMPRESS] Queue full, discarded task {old_task.get('id', 'unknown')}")
                
                # 添加新任务
                if priority == 'high':
                    # 高优先级任务插入到队列前面
                    self.compression_queue.appendleft(task)
                else:
                    # 普通优先级任务插入到队列后面
                    self.compression_queue.append(task)
            
            app_logger.info(f"📦 [COMPRESS] Queued compression task for {user_id}:{conversation_id} with priority {priority}")
            
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Failed to queue compression task: {e}")
    
    async def _compression_processor(self) -> None:
        """异步压缩处理器"""
        while True:
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
                app_logger.error(f"❌ [COMPRESS] Compression processor error: {e}")
                await asyncio.sleep(5)
    
    async def _process_compression_task(self, task: Dict[str, Any]) -> None:
        """处理单个压缩任务"""
        try:
            user_id = task['user_id']
            conversation_id = task['conversation_id']
            task_id = task['id']
            
            app_logger.info(f"🔄 [COMPRESS] Processing compression task {task_id} for {user_id}:{conversation_id}")
            
            # 获取对话消息
            from database import conversation_repo
            all_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            if not all_messages:
                return
            
            # 执行递增总结压缩
            await self.incremental_compression(user_id, conversation_id, all_messages)
            
            app_logger.info(f"✅ [COMPRESS] Completed compression task {task_id} for {user_id}:{conversation_id}")
            
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Failed to process compression task {task.get('id', 'unknown')}: {e}")
        finally:
            # 线程安全地减少活跃压缩计数
            with self.compression_lock:
                self.active_compressions = max(0, self.active_compressions - 1)
    
    async def incremental_compression(
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
                app_logger.info(f"ℹ️ [COMPRESS] No messages need summarization for {user_id}:{conversation_id}")
                return True
            
            # 生成各层摘要
            previous_summary = ""
            for layer in ['L1', 'L2', 'L3']:
                layer_summary = await summary_generator.generate_layer_summary(
                    layer=layer,
                    messages=messages_to_summarize,
                    previous_summary=previous_summary
                )
                
                if layer_summary:
                    new_summaries[layer] = layer_summary
                    previous_summary = layer_summary
            
            # 存储各层摘要
            if new_summaries:
                await self._store_layer_summaries(user_id, conversation_id, new_summaries)
            
            # 清理旧消息（只保留最近的）
            await self._cleanup_old_messages(user_id, conversation_id, messages_to_keep)
            
            app_logger.info(f"✨ [COMPRESS] Incremental compression completed for {user_id}:{conversation_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Incremental compression failed: {e}")
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
                summary = await redis_manager.get_conversation_summary(
                    user_id, conversation_id, layer
                )
                if summary:
                    summaries[layer] = summary
            return summaries
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Failed to get existing summaries: {e}")
            return {}
    
    async def _store_layer_summaries(
        self,
        user_id: str,
        conversation_id: str,
        summaries: Dict[str, str]
    ) -> None:
        """存储各层摘要"""
        try:
            for layer, summary in summaries.items():
                await redis_manager.set_conversation_summary(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    layer=layer,
                    summary=summary
                )
            app_logger.info(f"💾 [COMPRESS] Stored {len(summaries)} layer summaries for {user_id}:{conversation_id}")
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Failed to store layer summaries: {e}")
    
    async def _cleanup_old_messages(
        self,
        user_id: str,
        conversation_id: str,
        messages_to_keep: List[Dict[str, Any]]
    ) -> None:
        """清理旧消息，只保留指定的消息"""
        try:
            # 从Redis中清除旧消息，只保留最近的
            from database import conversation_repo
            
            # 获取所有消息ID
            all_message_ids = {msg.get('id') for msg in messages_to_keep if msg.get('id')}
            
            # 获取数据库中的所有消息
            db_messages = conversation_repo.get_current_conversation_messages(
                conversation_id=conversation_id,
                limit=100
            )
            
            # 删除不在保留列表中的消息
            deleted_count = 0
            for msg in db_messages:
                msg_id = msg.get('id')
                if msg_id and msg_id not in all_message_ids:
                    # 从Redis中删除
                    try:
                        conv_id = f"{user_id}:{conversation_id}:{msg_id}"
                        await redis_manager.delete_conversation_message(
                            user_id, conversation_id, conv_id
                        )
                        deleted_count += 1
                    except Exception as delete_error:
                        app_logger.warning(f"⚠️ [COMPRESS] Failed to delete message {conv_id}: {delete_error}")
            
            app_logger.info(f"🗑️ [COMPRESS] Cleanup completed for {user_id}:{conversation_id} - kept {len(messages_to_keep)} messages, deleted {deleted_count} old messages")
            
        except Exception as e:
            app_logger.error(f"❌ [COMPRESS] Failed to cleanup old messages: {e}")


# 全局实例
memory_compressor = MemoryCompressor()

