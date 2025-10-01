# 对话机器人记忆系统设计方案

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    用户发送消息                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│               Chat Service (聊天服务)                        │
│  1. 提取上下文                                               │
│  2. 生成回复                                                 │
│  3. 保存对话                                                 │
└────────────┬────────────────────────────────┬───────────────┘
             ↓                                ↓
┌────────────────────────┐      ┌───────────────────────────┐
│   短期记忆              │      │   长期记忆                 │
│  (Working Memory)      │      │  (Long-term Memory)       │
└────────────────────────┘      └───────────────────────────┘
```

## 1. 短期记忆 (Working Memory)

### 目的
维护当前对话上下文，让AI能理解最近的对话内容。

### 实现方式

#### 方案A：直接读取 + 智能压缩（推荐）
```python
def get_short_term_context(conversation_id, max_tokens=1000):
    """获取短期记忆上下文"""
    # 1. 从数据库读取最近消息
    messages = db.get_messages(conversation_id)
    
    # 2. 计算token数
    total_tokens = count_tokens(messages)
    
    # 3. 如果超过阈值，进行压缩
    if total_tokens > max_tokens:
        # 保留最近3轮对话（原始）
        recent = messages[-6:]
        
        # 旧对话做summary
        old_messages = messages[:-6]
        summary = await llm_summarize(old_messages)
        
        return {
            'summary': summary,  # 旧对话的摘要
            'recent': recent     # 最近对话的原文
        }
    else:
        return {
            'summary': None,
            'recent': messages
        }
```

#### 方案B：滑动窗口 + 缓存
```python
class ShortTermMemory:
    """短期记忆管理器"""
    
    def __init__(self):
        self.max_tokens = 1000
        self.summary_cache = {}  # 缓存summary
    
    async def get_context(self, conversation_id):
        messages = db.get_messages(conversation_id)
        tokens = count_tokens(messages)
        
        if tokens <= self.max_tokens:
            return messages
        
        # 检查缓存
        cache_key = f"{conversation_id}:{len(messages)-6}"
        if cache_key in self.summary_cache:
            summary = self.summary_cache[cache_key]
        else:
            # 生成新的summary
            old = messages[:-6]
            summary = await self.generate_summary(old)
            self.summary_cache[cache_key] = summary
        
        return {
            'summary': summary,
            'recent': messages[-6:]
        }
```

### 触发时机
- **每次对话时**：检查token数
- **超过阈值**：自动触发summary
- **缓存机制**：避免重复计算

## 2. 长期记忆 (Long-term Memory)

### 2.1 语义记忆 (Semantic Memory)

#### 用户偏好 (User Preferences)
```json
{
  "user_id": "user_123",
  "preferences": {
    "interests": ["AI", "编程", "音乐"],
    "dislikes": ["数学公式", "长篇大论"],
    "communication_style": "简洁直接",
    "language": "中文",
    "timezone": "Asia/Shanghai"
  },
  "updated_at": "2025-10-01T17:30:00"
}
```

**提取方式**：
```python
async def extract_preferences(user_id, message, response):
    """从对话中提取用户偏好"""
    
    # 检测关键信号
    preference_signals = {
        "我喜欢": "interest",
        "我不喜欢": "dislike", 
        "我讨厌": "dislike",
        "我是": "identity",
        "我在": "location"
    }
    
    # 使用LLM智能提取
    prompt = f"""
    从以下对话中提取用户偏好信息：
    用户: {message}
    助手: {response}
    
    提取格式：
    {{
        "interests": [],
        "dislikes": [],
        "identity": {{}},
        "other": {{}}
    }}
    """
    
    preferences = await llm_extract(prompt)
    await update_user_profile(user_id, preferences)
```

### 2.2 情景记忆 (Episodic Memory)

#### 定义
记录重要的对话事件和用户经历。

```json
{
  "episode_id": "ep_001",
  "user_id": "user_123",
  "timestamp": "2025-10-01T10:00:00",
  "event_type": "important_question",
  "summary": "用户询问如何学习Python",
  "context": {
    "intent": "search",
    "sentiment": "curious",
    "topics": ["Python", "学习"]
  },
  "importance_score": 0.85
}
```

**存储策略**：
```python
async def save_episode(conversation_id, message, response, intent):
    """保存情景记忆"""
    
    # 1. 判断重要性
    importance = calculate_importance(message, response, intent)
    
    # 2. 只保存重要对话（importance > 0.7）
    if importance > 0.7:
        episode = {
            'conversation_id': conversation_id,
            'summary': await generate_summary(message, response),
            'topics': extract_topics(message),
            'intent': intent,
            'importance': importance,
            'embedding': await generate_embedding(message + response)
        }
        
        # 3. 存储到向量数据库
        await vector_db.store(episode)
```

**重要性评分因素**：
- 对话长度（长对话更重要）
- Intent类型（search/file/web > normal）
- 用户情感（强烈情感更重要）
- 是否包含决策或承诺
- 是否涉及个人信息

## 3. 记忆检索策略

### 3.1 短期记忆检索
```python
async def retrieve_short_term(conversation_id):
    """检索短期记忆"""
    context = await short_term_memory.get_context(conversation_id)
    
    # 构建prompt
    if context['summary']:
        prompt = f"""
        对话历史摘要：
        {context['summary']}
        
        最近对话：
        {format_messages(context['recent'])}
        """
    else:
        prompt = format_messages(context['recent'])
    
    return prompt
```

### 3.2 长期记忆检索
```python
async def retrieve_long_term(user_id, current_message):
    """检索长期记忆"""
    
    # 1. 获取用户偏好
    preferences = await get_user_preferences(user_id)
    
    # 2. 语义搜索相关情景
    query_embedding = await generate_embedding(current_message)
    episodes = await vector_db.search(
        query_embedding,
        filter={'user_id': user_id},
        limit=3,
        min_score=0.7
    )
    
    # 3. 构建上下文
    context = f"""
    用户偏好：
    - 兴趣：{', '.join(preferences['interests'])}
    - 风格：{preferences['communication_style']}
    
    相关历史：
    {format_episodes(episodes)}
    """
    
    return context
```

## 4. 完整的对话流程

```python
async def handle_message(user_id, conversation_id, message):
    """处理用户消息"""
    
    # 1. 检索短期记忆
    short_term = await retrieve_short_term(conversation_id)
    
    # 2. 检索长期记忆
    long_term = await retrieve_long_term(user_id, message)
    
    # 3. 生成回复
    response = await ai_service.generate(
        message=message,
        short_term_context=short_term,
        long_term_context=long_term
    )
    
    # 4. 保存对话到数据库
    await db.save_message(conversation_id, 'user', message)
    await db.save_message(conversation_id, 'assistant', response)
    
    # 5. 更新记忆（异步，不阻塞响应）
    asyncio.create_task(update_memories(
        user_id, conversation_id, message, response
    ))
    
    return response

async def update_memories(user_id, conversation_id, message, response):
    """更新记忆系统（后台任务）"""
    
    # 1. 提取用户偏好
    preferences = await extract_preferences(user_id, message, response)
    if preferences:
        await update_user_profile(user_id, preferences)
    
    # 2. 保存重要情景
    await save_episode_if_important(
        user_id, conversation_id, message, response
    )
    
    # 3. 检查是否需要压缩短期记忆
    await short_term_memory.check_and_compress(conversation_id)
```

## 5. 性能优化

### 5.1 缓存策略
```python
# 使用Redis缓存
- 用户偏好：TTL 1小时
- Summary：TTL 30分钟  
- 情景检索结果：TTL 5分钟
```

### 5.2 异步处理
```python
# 不阻塞主流程
- 偏好提取：后台任务
- 情景保存：后台任务
- Summary生成：延迟到需要时
```

### 5.3 批处理
```python
# 批量处理记忆更新
- 每10条消息触发一次批量偏好提取
- 每50条消息触发一次情景整理
```

## 6. 推荐的优先级实施

### Phase 1（当前）：基础功能
✅ 数据库存储所有对话
✅ 从数据库读取短期记忆
✅ 基本的长期记忆存储

### Phase 2（建议立即实施）：智能压缩
🎯 实现token计数
🎯 超过1k token自动生成summary
🎯 Summary缓存机制

### Phase 3（中期）：用户偏好
🎯 自动提取用户偏好
🎯 偏好驱动的个性化回复
🎯 偏好可视化管理

### Phase 4（长期）：高级情景记忆
🎯 智能重要性评分
🎯 多维度情景检索
🎯 记忆整合与遗忘机制

## 7. API设计建议

### 内部API（后端调用）
```python
# services/memory_service.py
class MemoryService:
    async def get_short_term_context(conversation_id)
    async def get_long_term_context(user_id, query)
    async def update_memories(user_id, conversation_id, message, response)
    async def extract_preferences(user_id, message)
    async def save_episode(episode_data)
```

### 管理API（可选，用于调试）
```python
# api/v1/memory.py (admin only)
GET  /admin/memory/user/{user_id}/preferences
GET  /admin/memory/user/{user_id}/episodes
POST /admin/memory/clear/{user_id}
GET  /admin/memory/stats
```

## 总结

你的设计思路是正确的！建议的改进：

1. **短期记忆**：
   - ✅ 从数据库实时读取
   - ➕ 添加智能压缩（>1k tokens）
   - ➕ 缓存summary结果

2. **长期记忆**：
   - ➕ 明确区分：用户偏好 + 情景记忆
   - ➕ 自动提取和更新
   - ➕ 重要性评分机制

3. **API设计**：
   - ✅ 内部调用为主
   - ➕ 管理API标记为admin
   - ➕ 前端无需关心记忆系统

