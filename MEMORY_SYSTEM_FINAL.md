# 智能记忆系统 - 最终实现方案

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    对话流程                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴──────────────┐
                ↓                            ↓
        【提取上下文】                  【保存记忆】
                │                            │
    ┌───────────┼───────────┐    ┌──────────┼──────────┐
    ↓           ↓           ↓    ↓          ↓          ↓
短期记忆    用户画像   语义记忆  数据库   偏好提取   向量库
```

## 三层记忆详解

### 1. 短期记忆（Working Memory）

**来源**：SQLite数据库  
**策略**：智能压缩

```python
# 自动检测token数
messages = db.get_messages(conversation_id)
tokens = count_tokens(messages)

if tokens <= 1000:
    # 直接返回全部对话
    return format_all(messages)
else:
    # 智能压缩
    recent = messages[-6:]  # 最近3轮原文
    old = messages[:-6]     # 旧对话
    summary = await llm_summarize(old)  # LLM总结
    
    return f"""
    【对话历史摘要】（{len(old)}条消息）
    {summary}
    
    【最近对话】
    {format(recent)}
    """
```

**效果**：
- 小于1k tokens：全部保留 ✅
- 大于1k tokens：自动压缩 70%+ ✅
- 缓存机制：避免重复生成 ✅

### 2. 用户画像/偏好（User Profile）

**来源**：自动从对话中提取  
**存储**：Redis缓存（快速访问）

**自动提取触发**：
```python
# 检测偏好信号词
signals = ["我喜欢", "我不喜欢", "我是", "我在", "我的", "我想"]

if any(signal in message for signal in signals):
    # 调用LLM提取
    profile = await extract_identity(message)
    # 保存到Redis
    await save_user_profile(user_id, profile)
```

**提取内容**：
```json
{
  "identity": {
    "name": "张三",
    "age": 25,
    "location": "北京",
    "job": "软件工程师"
  },
  "interests": ["AI", "编程", "音乐"],
  "preferences": ["简洁的回答", "代码示例"],
  "communication_style": "专业、友好"
}
```

**使用方式**：
```python
# 在生成回复时自动注入
profile = await get_user_profile(user_id)

system_prompt = f"""
你在和{profile['name']}对话，他是{profile['job']}，
喜欢{profile['interests']}。
请用{profile['communication_style']}的方式回答。
"""
```

### 3. 语义记忆（Episodic Memory）

**来源**：重要对话（评分>0.6）  
**存储**：Qdrant向量数据库  
**检索**：语义相似度搜索

**保存策略**：
```python
# 计算重要性评分
importance = calculate_importance(message, response, intent)

评分因素：
- 对话长度（长对话 +0.3）
- Intent类型（search/file/web +0.4）
- 决策词汇（"决定"/"计划" +0.2）
- 个人信息（"我的"/"我想" +0.1）

if importance >= 0.6:
    # 保存到向量数据库
    memory_text = f"问题：{message}\n回答：{response}"
    embedding = await generate_embedding(memory_text)
    await vector_db.store(embedding, memory_text, metadata)
```

**检索策略**：
```python
# 当用户提问时，语义搜索相似对话
current_question = "如何学习Python？"
query_embedding = await generate_embedding(current_question)

# 搜索最相似的3条历史对话
similar = await vector_db.search(query_embedding, limit=3)

# 返回：
# 1. 问题：什么是Python？回答：...
# 2. 问题：推荐编程书籍？回答：...  
# 3. 问题：如何入门编程？回答：...
```

## 完整工作流程

### 用户发送消息

```
1. 提取上下文阶段
   ├─ 获取短期记忆（数据库 + 智能压缩）
   ├─ 获取用户画像（Redis缓存）
   └─ 语义搜索相似对话（向量数据库）
   
2. 生成回复（使用记忆增强的上下文）
   
3. 保存到数据库（所有对话）
   
4. 异步更新长期记忆（后台任务，不阻塞）
   ├─ 检测偏好信号 -> 提取画像
   └─ 计算重要性 -> 保存到向量库
```

## 实际使用示例

### 场景1：短对话（无压缩）

```
第1轮
用户: 你好
助手: 你好！

第2轮  
用户: 今天天气怎么样？
助手: 让我搜索一下...

总tokens: ~300
结果: 全部原文，不压缩
```

### 场景2：长对话（自动压缩）

```
经过20轮对话后...

总tokens: ~2500 (超过1000!)

AI看到的上下文：
【对话历史摘要】（14条消息）
用户询问了Python学习方法、数据分析、
机器学习入门等话题。助手提供了详细的
教程和代码示例。

【最近对话】
用户: 如何用pandas读取CSV？
助手: 使用pd.read_csv()...
用户: 能画个图吗？
助手: 当然可以...
用户: matplotlib怎么用？
助手: 导入库后使用...

压缩效果: 2500 tokens -> 800 tokens (68%压缩率)
```

### 场景3：偏好提取（自动）

```
用户: "我是张三，在北京工作，喜欢看科幻小说"

系统自动：
1. 检测到偏好信号词 ✅
2. 调用LLM提取：
   {
     "name": "张三",
     "location": "北京", 
     "interests": ["科幻小说"]
   }
3. 保存到Redis ✅
4. 下次对话自动使用 ✅

下一轮对话：
用户: "推荐一本书"
助手: "张三，根据你喜欢科幻小说，推荐《三体》..."
      ↑ 自动记住了用户画像！
```

### 场景4：语义记忆（智能检索）

```
第5轮（1个月前）
用户: "Python的装饰器怎么用？"
助手: [详细讲解装饰器...]
重要性: 0.85 -> 保存到向量库 ✅

第50轮（今天）
用户: "闭包和装饰器有什么关系？"

系统自动：
1. 当前问题生成embedding
2. 在向量库中语义搜索
3. 找到第5轮的装饰器对话 ✅
4. 作为上下文注入

AI回复: "还记得之前我们讨论过装饰器，
现在来说闭包的关系..."
↑ 跨越50轮对话，仍然记得！
```

## 技术实现要点

### 1. Token计数
```python
import tiktoken
encoder = tiktoken.encoding_for_model("gpt-4")
tokens = len(encoder.encode(text))
```

### 2. 摘要缓存
```python
cache_key = f"{conversation_id}:{old_message_count}"
if cache_key in cache:
    summary = cache[cache_key]
else:
    summary = await llm_summarize(old_messages)
    cache[cache_key] = summary
```

### 3. 异步处理
```python
# 主流程：快速返回
response = await generate_response(...)
return response  # 200ms

# 后台任务：不阻塞
asyncio.create_task(
    update_memories_async(...)
)  # 500ms，用户无感
```

### 4. 向量搜索
```python
# 当前问题
query = "如何学习Python？"
embedding = await generate_embedding(query)

# 语义搜索
results = await vector_db.search(
    embedding,
    filter={'user_id': user_id},
    limit=3,
    min_score=0.7  # 相似度阈值
)
```

## 优势

✅ **智能自适应**：短对话不压缩，长对话自动压缩  
✅ **全自动**：用户画像自动提取，无需手动输入  
✅ **语义检索**：跨对话搜索相关历史，不限于当前对话  
✅ **性能优化**：缓存、异步处理，不影响响应速度  
✅ **成本可控**：只保存重要对话，节省存储和API调用  

## API设计（后端自动，前端无感）

### 前端开发者
```javascript
// 只需要调用一个API
POST /api/v1/chat/stream
{
  "message": "你好",
  "conversationId": "conv_123"
}

// 记忆系统完全自动工作！
// - 自动提取用户画像
// - 自动压缩对话历史
// - 自动检索相关记忆
// - 自动保存重要对话
```

### 后端开发者
```python
# 一切都在 chat_service 中自动完成
async def process_chat():
    # 1. 自动提取记忆上下文
    context = await extract_user_context(...)
    
    # 2. 生成回复
    response = await generate_response(context)
    
    # 3. 异步更新记忆
    asyncio.create_task(update_memories(...))
```

### 管理员（可选）
```bash
# 查看用户画像
GET /api/v1/memory/user-identity/{user_id}

# 查看记忆统计
GET /api/v1/memory/stats/{user_id}
```

## 总结

这套记忆系统完美实现了你的设计理念：
- ✅ 短期记忆：超过1k token自动summary
- ✅ 用户画像：自动提取偏好和兴趣
- ✅ 语义记忆：向量数据库 + 语义搜索
- ✅ 完全自动：后端处理，前端无感

