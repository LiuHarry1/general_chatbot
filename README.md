# AI Assistant - Professional Chatbot

一个专业的AI聊天机器人，支持对话、文件上传分析、网页内容分析和网络搜索功能。

## 🚀 快速开始

### 启动方式

#### 推荐方式（一键启动）
```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

#### 单独启动
```bash
# 仅启动前端
./start-client.sh

# 仅启动后端  
./start-server.sh

# 或手动启动
cd client && npm start    # 前端 (端口 3000)
cd server && python main.py  # 后端 (端口 3001)
```

### 配置环境变量

1. 复制环境变量模板：
```bash
cp env.example .env
```

2. 编辑 `.env` 文件，添加API密钥：
```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
PORT=3001
REACT_APP_API_URL=http://localhost:3001/api
```

### 访问应用

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:3001
- **API文档**: http://localhost:3001/docs

## ✨ 功能特性

- 💬 **智能对话**: 基于通义千问模型的自然语言对话
- 🔍 **网络搜索**: 集成Tavily搜索工具，实时获取最新信息
- 📄 **文件分析**: 支持PDF、DOC、DOCX、TXT、MD文件上传和分析
- 🌐 **网页分析**: 分析指定网页内容并回答问题
- 📱 **响应式设计**: 现代化的UI设计，支持移动端
- 📝 **Markdown支持**: 完整的Markdown渲染和代码高亮
- 📊 **对话历史**: 可管理的对话历史记录

## 🎯 使用指南

### 界面布局
```
┌─────────────────────────────────────────────────────────────┐
│ [☰] AI Assistant                                    [U]     │
├─────────────┬───────────────────────────────────────────────┤
│ 侧边栏      │ 聊天区域                                        │
│             │                                               │
│ [New Chat]  │ 欢迎界面 / 对话消息                            │
│             │                                               │
│ 对话历史    │                                               │
│ - 对话1     │                                               │
│ - 对话2     │                                               │
│             │ ┌─────────────────────────────────────────┐   │
│             │ │ 输入框 [📎] [🔗] [发送]                  │   │
│             │ └─────────────────────────────────────────┘   │
└─────────────┴───────────────────────────────────────────────┘
```

### 基本对话
- 在输入框中输入问题，按 `Enter` 发送
- 按 `Shift + Enter` 换行
- AI会基于通义千问模型回答

### 文件上传分析
1. 点击输入框右侧的 📎 图标
2. 选择支持的文件：PDF、DOC、DOCX、TXT、MD
3. **支持同时上传多个文件** - 可以一次性选择多个文件进行批量分析
4. 文件会被自动解析，AI会综合分析所有文件内容
5. 上传的文件会显示在输入框上方，可点击 ❌ 删除单个文件
6. AI在回答时会说明信息来自哪个文件（当有多个文件时）

### 网页内容分析
1. 点击输入框右侧的 🔗 图标
2. 输入要分析的网页URL
3. AI会分析网页内容并基于内容回答
4. 分析的网页会显示在输入框上方，可点击 ❌ 删除

### 网络搜索
当问题包含搜索关键词时自动触发：
- 英文：search、find、look up、what is、how to、where is
- 中文：搜索、查找、寻找、什么是、如何、哪里、最新、新闻

### 对话管理
- 左侧显示所有对话历史
- 点击"New Conversation"创建新对话
- 点击对话项切换对话
- 悬停显示删除按钮

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS
- Lucide React (图标)
- React Markdown (Markdown渲染)
- React Syntax Highlighter (代码高亮)

### 后端
- FastAPI (Python)
- 通义千问 API
- Tavily 搜索 API
- 文件处理 (PDF、Word、文本)
- 网页内容抓取
- 结构化日志

## 📁 项目结构

```
general_chatbot/
├── client/                 # React 前端应用
│   ├── src/               # React 源代码
│   ├── package.json       # 前端依赖管理
│   └── start.sh/bat       # 前端启动脚本
├── server/                # Python 后端服务
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑服务
│   ├── utils/             # 工具函数
│   ├── logs/              # 日志文件
│   ├── requirements.txt   # Python 依赖
│   ├── main.py            # 主程序入口 (FastAPI)
│   └── start.sh/bat       # 后端启动脚本
├── start.sh/bat           # 主启动脚本 (启动前后端)
├── stop.sh/bat            # 主停止脚本
├── env.example            # 环境变量模板
└── README.md              # 项目说明
```

## 🔧 故障排除

### PowerShell执行策略错误
如果遇到 "无法加载文件 npm.ps1，因为在此系统上禁止运行脚本" 的错误：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 端口被占用
如果3000或3001端口被占用：
- 前端：在 `client/package.json` 中修改 `start` 脚本
- 后端：在 `.env` 中修改 `PORT`

### 依赖安装失败
```bash
# 清除缓存重新安装
npm cache clean --force
rm -rf node_modules client/node_modules
npm install
cd client && npm install
```

### API调用失败
1. 检查 `.env` 文件中的API密钥
2. 查看控制台错误信息
3. 检查网络连接

### 常见问题

1. **文件上传失败**
   - 检查文件大小（限制10MB）
   - 确认文件类型支持
   - 检查网络连接

2. **网页分析失败**
   - 确认URL可访问
   - 检查网页是否包含文本内容
   - 某些网站可能有反爬虫保护

3. **AI回答异常**
   - 检查API密钥配置
   - 查看控制台错误信息
   - 检查网络连接

## 📖 API文档

### 基础信息
- **基础URL**: `http://localhost:3001/api`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 主要API端点

#### 1. 健康检查
```bash
GET /api/health
# 响应: {"status": "OK", "timestamp": "...", "uptime": 1234.567}
```

#### 2. 聊天对话
```bash
POST /api/chat
{
  "message": "用户消息内容",
  "conversationId": "对话ID",
  "attachments": [{"type": "file", "data": {"name": "文件名", "content": "文件内容"}}]
}
```

#### 3. 文件上传
```bash
POST /api/upload
# 支持: PDF, DOC, DOCX, TXT, MD (最大10MB)
```

#### 4. 网页分析
```bash
POST /api/analyze-url
{"url": "https://example.com"}
```

### 使用示例

```bash
# 普通对话
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下自己", "conversationId": "conv_001"}'

# 文件分析
curl -X POST http://localhost:3001/api/upload -F "file=@document.pdf"

# 网页分析
curl -X POST http://localhost:3001/api/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 📁 项目结构

```
general_chatbot/
├── client/                 # React 前端应用
│   ├── src/               # React 源代码
│   │   ├── components/    # UI组件
│   │   ├── hooks/         # React Hooks
│   │   ├── services/      # API服务
│   │   └── utils/         # 工具函数
│   ├── package.json       # 前端依赖管理
│   └── start.sh/bat       # 前端启动脚本
├── server/                # Python 后端服务
│   ├── api/               # API 路由
│   │   └── v1/            # API版本1
│   ├── services/          # 业务逻辑服务
│   ├── models/            # 数据模型
│   ├── config/            # 配置管理
│   ├── memory_simple/     # 记忆系统
│   ├── database/          # 数据访问层
│   ├── utils/             # 工具函数
│   ├── logs/              # 日志文件
│   ├── requirements.txt   # Python 依赖
│   ├── main.py            # 主程序入口
│   └── start.sh/bat       # 后端启动脚本
├── tests/                 # 测试框架
├── start.sh/bat           # 主启动脚本
├── stop.sh/bat            # 主停止脚本
├── env.example            # 环境变量模板
└── README.md              # 项目说明
```

### 代码分离原则
- ✅ **前端代码** 仅放在 `client/` 目录下
- ✅ **Python 后端代码** 仅放在 `server/` 目录下
- ✅ **日志文件** 统一放在 `server/logs/` 目录下
- ✅ **启动/停止脚本** 各自在对应目录下，根目录脚本调用子目录脚本

## 🚀 部署

### 生产环境构建
```bash
# 构建前端
cd client
npm run build

# 启动生产服务器
cd server
python main.py
```

### 环境变量
确保在生产环境中设置正确的环境变量：
- `DASHSCOPE_API_KEY`: 通义千问API密钥
- `TAVILY_API_KEY`: Tavily搜索API密钥
- `PORT`: 服务器端口（默认3001）

## 📚 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技术架构文档（开发者指南）

## 📄 许可证

MIT License