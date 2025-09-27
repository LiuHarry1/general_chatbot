# AI Assistant - Professional Chatbot

一个专业的AI聊天机器人，支持对话、文件上传分析、网页内容分析和网络搜索功能。

## 功能特性

- 💬 **智能对话**: 基于通义千问模型的自然语言对话
- 🔍 **网络搜索**: 集成Tavily搜索工具，实时获取最新信息
- 📄 **文件分析**: 支持PDF、DOC、DOCX、TXT、MD文件上传和分析
- 🌐 **网页分析**: 分析指定网页内容并回答问题
- 📱 **响应式设计**: 现代化的UI设计，支持移动端
- 📝 **Markdown支持**: 完整的Markdown渲染支持
- 📊 **对话历史**: 可管理的对话历史记录
- 🎨 **专业界面**: 基于UX设计原则的专业界面

## 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS
- Lucide React (图标)
- React Markdown (Markdown渲染)
- React Syntax Highlighter (代码高亮)

### 后端
- Node.js + Express
- 通义千问 API
- Tavily 搜索 API
- Multer (文件上传)
- Winston (日志系统)
- Cheerio (网页解析)
- Mammoth (Word文档解析)
- PDF-Parse (PDF解析)

## 快速开始

### 1. 安装依赖

```bash
# 安装根目录依赖
npm install

# 安装前端依赖
cd client
npm install
cd ..

# 安装后端依赖（已在根目录安装）
```

### 2. 配置环境变量

复制 `env.example` 到 `.env` 并填入你的API密钥：

```bash
cp env.example .env
```

编辑 `.env` 文件：
```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
PORT=3001
REACT_APP_API_URL=http://localhost:3001/api
```

### 3. 启动应用

```bash
# 同时启动前端和后端
npm run dev

# 或者分别启动
npm run server  # 启动后端 (端口 3001)
npm run client  # 启动前端 (端口 3000)
```

### 4. 访问应用

打开浏览器访问 `http://localhost:3000`

## 使用说明

### 基本对话
直接在输入框中输入问题，按Enter发送，Shift+Enter换行。

### 文件上传
1. 点击输入框右侧的📎图标
2. 选择支持的文件类型（PDF、DOC、DOCX、TXT、MD）
3. 文件会被自动分析，AI将基于文件内容回答问题

### 网页分析
1. 点击输入框右侧的🔗图标
2. 输入要分析的网页URL
3. AI将分析网页内容并基于内容回答问题

### 网络搜索
当你的问题包含搜索关键词时，AI会自动使用Tavily进行网络搜索。

### 对话管理
- 左侧边栏显示所有对话历史
- 点击"New Conversation"创建新对话
- 点击对话项切换对话
- 悬停对话项显示删除按钮

## 项目结构

```
chatbot_test/
├── client/                 # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── services/       # API服务
│   │   ├── types.ts        # TypeScript类型定义
│   │   └── ...
│   └── package.json
├── server/                 # Node.js后端
│   └── index.js           # Express服务器
├── logs/                  # 日志文件
├── uploads/               # 临时文件上传目录
├── package.json           # 根目录依赖
└── README.md
```

## API接口

### POST /api/chat
发送聊天消息
```json
{
  "message": "用户消息",
  "conversationId": "对话ID",
  "attachments": [{"type": "file", "data": {...}}]
}
```

### POST /api/upload
上传文件
- Content-Type: multipart/form-data
- 支持文件类型: PDF, DOC, DOCX, TXT, MD

### POST /api/analyze-url
分析网页
```json
{
  "url": "https://example.com"
}
```

## 开发说明

### 添加新功能
1. 前端组件放在 `client/src/components/`
2. API服务放在 `client/src/services/`
3. 后端路由在 `server/index.js` 中添加

### 日志系统
使用Winston进行日志记录：
- 错误日志: `logs/error.log`
- 综合日志: `logs/combined.log`
- 控制台输出: 开发环境

### 错误处理
- 前端: 组件级别的错误边界
- 后端: 全局错误处理中间件
- API: 统一的错误响应格式

## 部署

### 生产环境构建
```bash
# 构建前端
cd client
npm run build

# 启动生产服务器
cd ..
npm start
```

### 环境变量
确保在生产环境中设置正确的环境变量：
- `DASHSCOPE_API_KEY`: 通义千问API密钥
- `TAVILY_API_KEY`: Tavily搜索API密钥
- `PORT`: 服务器端口（默认3001）

## 许可证

MIT License


