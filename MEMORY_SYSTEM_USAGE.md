# 现代化记忆系统使用指南

## 🎯 系统概述

本系统实现了一个现代化的生产级记忆管理架构，包含短期记忆、长期记忆、用户画像和语义搜索功能。

## 🏗️ 架构组件

### 1. 存储层
- **Qdrant**: 向量数据库，存储语义记忆和知识图谱
- **Redis**: 缓存层，存储用户画像和会话数据
- **SQLite**: 关系数据库，存储记忆索引和元数据

### 2. 核心服务
- **ModernMemoryManager**: 统一记忆管理接口
- **ImportanceCalculator**: 重要性评分算法
- **CompressionService**: 智能对话压缩
- **ProfileService**: 用户画像管理
- **SemanticSearchService**: 语义搜索服务

## 🚀 快速开始

### 1. 环境准备

确保以下服务正在运行：
```bash
# Redis
redis-server

# Qdrant (使用Docker)
docker run -p 6333:6333 qdrant/qdrant
```

### 2. 数据库初始化

系统会自动创建必要的数据库表和索引。

### 3. API使用

#### 处理对话
```python
POST /api/v1/memory/process
{
    "user_id": "user123",
    "conversation_id": "conv456",
    "message": "我喜欢喝咖啡",
    "response": "好的，我记住了您喜欢咖啡",
    "intent": "normal",
    "sources": []
}
```

#### 获取对话上下文
```python
GET /api/v1/memory/context/{user_id}/{conversation_id}?current_message=你好
```

#### 搜索记忆
```python
POST /api/v1/memory/search
{
    "query": "咖啡",
    "user_id": "user123",
    "limit": 10
}
```

#### 获取用户画像
```python
GET /api/v1/memory/profile/{user_id}
```

## 📊 功能特性

### 1. 智能压缩
- 自动检测对话长度
- 超过1000 tokens时触发压缩
- 保留最近3轮对话，旧对话生成摘要

### 2. 重要性评分
- 基于对话长度、意图、关键词、个人信息等因素
- 评分范围：0.0-1.0
- 超过0.6的对话自动存储到长期记忆

### 3. 用户画像
- 自动提取用户偏好、身份信息
- 支持姓名、年龄、职业、兴趣等
- 实时更新和合并

### 4. 语义搜索
- 基于向量相似度搜索
- 支持多类型记忆检索
- 智能排序和过滤

## 🔧 配置说明

### 记忆阈值配置
```python
# 在 modern_memory_manager.py 中
self.short_term_threshold = 1000  # tokens
self.long_term_threshold = 0.6    # importance score
self.max_recent_turns = 3         # 保留轮数
```

### 重要性评分权重
```python
# 在 importance_calculator.py 中
self.intent_weights = {
    'search': 0.4,
    'web': 0.4,
    'file': 0.4,
    'code': 0.3,
    'normal': 0.1
}
```

## 📈 监控和维护

### 健康检查
```python
GET /api/v1/memory/health
```

### 清理旧记忆
```python
POST /api/v1/memory/cleanup?days=30
```

### 获取用户洞察
```python
GET /api/v1/memory/insights/{user_id}
```

## 🎨 使用示例

### Python代码示例

```python
import asyncio
from memory.modern_memory_manager import modern_memory_manager

async def example_usage():
    # 处理对话
    result = await modern_memory_manager.process_conversation(
        user_id="user123",
        conversation_id="conv456",
        message="我喜欢喝咖啡，特别是拿铁",
        response="好的，我记住了您喜欢拿铁咖啡",
        intent="normal",
        sources=[]
    )
    print(f"重要性评分: {result['importance_score']}")
    
    # 获取对话上下文
    context, metadata = await modern_memory_manager.get_conversation_context(
        user_id="user123",
        conversation_id="conv456",
        current_message="推荐一些咖啡",
        limit=5
    )
    print(f"上下文: {context}")
    
    # 搜索记忆
    memories = await modern_memory_manager.search_memories(
        query="咖啡",
        user_id="user123",
        limit=5
    )
    print(f"找到 {len(memories)} 条相关记忆")

# 运行示例
asyncio.run(example_usage())
```

## 🔍 故障排除

### 常见问题

1. **Qdrant连接失败**
   - 检查Qdrant服务是否运行
   - 确认端口6333可访问

2. **Redis连接失败**
   - 检查Redis服务是否运行
   - 确认端口6379可访问

3. **嵌入生成失败**
   - 检查API密钥配置
   - 确认网络连接正常

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

## 📚 API文档

完整的API文档可在以下地址查看：
- Swagger UI: http://localhost:3001/docs
- ReDoc: http://localhost:3001/redoc

## 🤝 贡献指南

1. 遵循现有代码风格
2. 添加适当的日志记录
3. 编写单元测试
4. 更新文档

## 📄 许可证

本项目采用MIT许可证。

