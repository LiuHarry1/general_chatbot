# AI Chatbot API 文档

## 概述

这是一个基于通义千问和Tavily搜索的AI聊天机器人API，支持对话、文件分析、网页分析和网络搜索功能。

## 基础信息

- **基础URL**: `http://localhost:3001/api`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

当前版本无需认证，所有API端点都是公开的。

## API端点

### 1. 健康检查

#### GET /api/health

检查API服务状态。

**响应示例:**
```json
{
  "status": "OK",
  "timestamp": "2025-09-27T10:30:08.487Z",
  "uptime": 1234.567
}
```

### 2. 服务状态

#### GET /api/status

获取所有服务的详细状态。

**响应示例:**
```json
{
  "status": "OK",
  "timestamp": "2025-09-27T10:30:08.487Z",
  "services": {
    "tongyi": "Available",
    "tavily": "Available",
    "fileProcessing": "Available",
    "webAnalysis": "Available"
  },
  "version": "1.0.0"
}
```

### 3. 支持的文件格式

#### GET /api/supported-formats

获取支持的文件类型和限制。

**响应示例:**
```json
{
  "supportedFormats": [".pdf", ".txt", ".doc", ".docx", ".md"],
  "maxFileSize": "10MB",
  "description": "支持的文件格式和大小限制"
}
```

### 4. 聊天对话

#### POST /api/chat

与AI助手进行对话。

**请求参数:**
```json
{
  "message": "用户消息内容",
  "conversationId": "对话ID",
  "attachments": [
    {
      "type": "file",
      "data": {
        "name": "文件名",
        "content": "文件内容"
      }
    }
  ]
}
```

**响应示例:**
```json
{
  "content": "AI助手的回复",
  "intent": "normal|file|web",
  "sources": ["搜索结果URL1", "搜索结果URL2"],
  "timestamp": "2025-09-27T10:30:08.487Z"
}
```

**意图类型:**
- `normal`: 普通对话
- `file`: 基于文件内容回答
- `web`: 基于网页内容回答

### 5. 文件上传

#### POST /api/upload

上传并分析文档文件。

**请求格式:** `multipart/form-data`

**参数:**
- `file`: 文件对象 (必需)

**支持的文件类型:**
- PDF (.pdf)
- Word文档 (.doc, .docx)
- 文本文件 (.txt)
- Markdown文件 (.md)

**文件大小限制:** 10MB

**响应示例:**
```json
{
  "content": "提取的文本内容",
  "filename": "原始文件名",
  "size": 1024,
  "type": ".pdf",
  "extractedLength": 5000
}
```

### 6. 网页分析

#### POST /api/analyze-url

分析网页内容。

**请求参数:**
```json
{
  "url": "https://example.com"
}
```

**响应示例:**
```json
{
  "title": "网页标题",
  "content": "网页内容",
  "url": "https://example.com",
  "analyzedAt": "2025-09-27T10:30:08.487Z",
  "contentLength": 3000
}
```

## 错误处理

### 错误响应格式

```json
{
  "error": "错误类型",
  "message": "详细错误信息",
  "timestamp": "2025-09-27T10:30:08.487Z"
}
```

### 常见错误码

- `400`: 请求参数错误
- `404`: 接口不存在
- `500`: 服务器内部错误

## 使用示例

### 1. 普通对话

```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下自己",
    "conversationId": "conv_001"
  }'
```

### 2. 文件分析

```bash
curl -X POST http://localhost:3001/api/upload \
  -F "file=@document.pdf"
```

### 3. 网页分析

```bash
curl -X POST http://localhost:3001/api/analyze-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com"
  }'
```

### 4. 搜索功能

```bash
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "搜索最新的AI新闻",
    "conversationId": "conv_002"
  }'
```

## 日志记录

API会记录以下信息到日志文件：

- 请求详情
- 错误信息
- 处理时间
- 文件上传信息
- 搜索查询

日志文件位置：
- 错误日志: `logs/error.log`
- 综合日志: `logs/combined.log`

## 性能优化

- 文件内容限制在8000字符以内，避免token超限
- 网页内容限制在4000字符以内
- 支持并发请求处理
- 自动清理临时文件

## 安全考虑

- 文件类型验证
- 文件大小限制
- URL格式验证
- 错误信息脱敏（生产环境）

## 更新日志

### v1.0.0 (2025-09-27)
- 初始版本发布
- 支持基础对话功能
- 支持文件上传和分析
- 支持网页内容分析
- 支持Tavily网络搜索
- 集成通义千问模型


