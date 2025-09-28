# Mem0智能记忆系统集成指南

## 概述

本项目已集成基于Mem0概念的智能记忆管理系统，能够自动提取用户偏好数据，构建长期记忆，并为AI对话提供个性化上下文。

## 核心功能

### 1. 智能偏好提取
- **自动识别**：从自然语言中自动提取用户偏好、兴趣、习惯
- **多维度分析**：个人偏好、身份信息、兴趣领域、沟通风格
- **置信度评估**：为提取的信息提供置信度评分

### 2. 用户档案管理
- **动态更新**：实时更新用户档案信息
- **信息合并**：智能合并多次对话中的信息
- **完整性跟踪**：跟踪用户档案的完整性

### 3. 上下文感知对话
- **个性化提示词**：基于用户档案构建个性化系统提示词
- **相关记忆检索**：根据当前对话检索相关历史记忆
- **长期记忆应用**：在对话中应用长期记忆信息

## API接口

### 基础记忆API

#### 提取用户偏好
```bash
POST /api/mem0/extract-preferences
{
    "message": "我是刘浩，今年25岁，喜欢喝咖啡",
    "user_id": "user_001"
}
```

#### 获取用户档案
```bash
GET /api/mem0/user-profile/user_001
```

#### 获取相关记忆
```bash
POST /api/mem0/relevant-memories
{
    "user_id": "user_001",
    "query": "电影推荐",
    "limit": 5
}
```

#### 构建上下文提示词
```bash
POST /api/mem0/contextual-prompt
{
    "user_id": "user_001",
    "current_message": "你好，有什么好看的电影推荐吗？"
}
```

### 高级功能API

#### 存储对话摘要
```bash
POST /api/mem0/store-summary
{
    "user_id": "user_001",
    "summary": "用户询问了电影推荐",
    "metadata": {"topic": "entertainment"}
}
```

#### 获取记忆统计
```bash
GET /api/mem0/memory-stats/user_001
```

#### 健康检查
```bash
GET /api/mem0/health
```

## 使用示例

### Python代码示例

```python
from memory.mem0_manager import mem0_manager

# 提取用户偏好
preferences = await mem0_manager.extract_preferences_from_message(
    "我是刘浩，今年25岁，喜欢喝咖啡，住在北京", 
    "user_001"
)

# 获取用户档案
profile = await mem0_manager.get_user_profile("user_001")

# 构建上下文提示词
contextual_prompt = await mem0_manager.build_contextual_prompt(
    "user_001", 
    "有什么好看的电影推荐吗？"
)

# 获取相关记忆
memories = await mem0_manager.get_relevant_memories(
    "user_001", 
    "电影", 
    limit=5
)
```

### 对话流程示例

```
用户: "我是刘浩，今年25岁，喜欢喝咖啡"
系统: 提取偏好 → 存储到档案 → 构建上下文

用户: "有什么好看的电影推荐吗？"
系统: 检索相关记忆 → 发现用户喜欢科幻片 → 推荐科幻电影

用户: "我是谁？"
系统: 从档案中获取身份信息 → "你是刘浩，25岁，喜欢喝咖啡"
```

## 技术架构

### 核心组件

1. **Mem0MemoryManager**: 核心记忆管理器
2. **AI偏好提取**: 使用通义千问进行智能信息提取
3. **用户档案系统**: 动态用户档案管理
4. **上下文构建**: 智能上下文提示词生成

### 数据流

```
用户消息 → AI偏好提取 → 存储到记忆 → 更新用户档案 → 构建上下文 → AI响应
```

### 记忆类型

- **preference**: 用户偏好和习惯
- **identity**: 身份信息
- **interaction**: 交互历史
- **context**: 上下文信息
- **knowledge**: 知识信息

## 配置说明

### 环境变量
```bash
# 通义千问API配置
DASHSCOPE_API_KEY=your_api_key
QWEN_MODEL=qwen-turbo

# 记忆系统配置
MEMORY_TTL=86400  # 记忆过期时间（秒）
MAX_MEMORIES_PER_USER=1000  # 每用户最大记忆数
```

### 依赖包
```bash
pip install mem0ai langchain langchain-community
```

## 测试验证

### 运行测试脚本
```bash
python test_mem0.py
```

### 测试用例
1. 偏好信息提取
2. 用户档案管理
3. 上下文提示词构建
4. 相关记忆检索
5. 健康检查

## 性能优化

### 缓存策略
- 用户档案内存缓存
- 相关记忆LRU缓存
- AI提取结果缓存

### 批处理
- 批量偏好提取
- 批量记忆更新
- 异步处理优化

## 扩展功能

### 计划中的功能
1. **向量相似性搜索**: 使用嵌入向量进行更精确的记忆检索
2. **记忆重要性评分**: 基于使用频率和相关性评分记忆重要性
3. **多模态记忆**: 支持图像、音频等多媒体记忆
4. **记忆压缩**: 自动压缩和总结长期记忆

### 集成建议
1. **Redis缓存**: 用于分布式部署的记忆缓存
2. **向量数据库**: 用于大规模记忆的向量检索
3. **消息队列**: 用于异步记忆处理

## 故障排除

### 常见问题

1. **AI提取失败**
   - 检查API密钥配置
   - 验证网络连接
   - 查看日志错误信息

2. **记忆丢失**
   - 检查内存存储状态
   - 验证用户ID一致性
   - 查看存储日志

3. **性能问题**
   - 调整批处理大小
   - 优化缓存策略
   - 监控内存使用

### 日志监控
```bash
# 查看记忆系统日志
tail -f server/logs/app.log | grep -i memory

# 查看API调用日志
tail -f server/logs/app.log | grep -i mem0
```

## 总结

Mem0智能记忆系统为AI助手提供了强大的长期记忆能力，能够：

- ✅ **自动提取**用户偏好和身份信息
- ✅ **智能构建**个性化对话上下文
- ✅ **长期记忆**用户交互历史和偏好
- ✅ **个性化响应**基于用户档案的定制化回复

通过这个系统，AI助手能够真正"记住"用户，提供更加个性化和连贯的对话体验。
