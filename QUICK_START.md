# 🚀 快速启动指南

## 问题解决

### PowerShell执行策略错误
如果遇到 "无法加载文件 npm.ps1，因为在此系统上禁止运行脚本" 的错误，请运行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 启动方式

### 方式1：使用PowerShell脚本（推荐）
```powershell
.\start.ps1
```

### 方式2：使用批处理文件
```cmd
start.bat
```

### 方式3：手动启动
```bash
# 1. 安装依赖
npm install
cd client
npm install
cd ..

# 2. 启动应用
npm run dev
```

## 访问应用

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:3001
- **健康检查**: http://localhost:3001/api/health

## 配置API密钥

1. 复制 `env.example` 到 `.env`
2. 编辑 `.env` 文件，添加你的API密钥：

```env
DASHSCOPE_API_KEY=sk-f256c03643e9491fb1ebc278dd958c2d
TAVILY_API_KEY=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
PORT=3001
REACT_APP_API_URL=http://localhost:3001/api
```

## 功能测试

### 1. 基本对话
在输入框中输入 "你好"，按Enter发送

### 2. 文件上传
- 点击📎图标
- 上传PDF、DOC、TXT等文件
- AI会基于文件内容回答

### 3. 网页分析
- 点击🔗图标
- 输入网页URL
- AI会分析网页内容

### 4. 网络搜索
输入包含搜索关键词的问题，如：
- "搜索最新的AI新闻"
- "查找Python教程"
- "什么是机器学习"

## 故障排除

### 端口被占用
如果3000或3001端口被占用，可以修改端口：
- 前端：在 `client/package.json` 中修改 `start` 脚本
- 后端：在 `.env` 中修改 `PORT`

### 依赖安装失败
```bash
# 清除缓存重新安装
npm cache clean --force
rm -rf node_modules
rm -rf client/node_modules
npm install
cd client && npm install
```

### API调用失败
1. 检查 `.env` 文件中的API密钥
2. 查看控制台错误信息
3. 检查网络连接

## 开发模式

应用现在正在开发模式下运行：
- 前端支持热重载
- 后端支持自动重启
- 实时日志输出

按 `Ctrl+C` 停止服务器。


