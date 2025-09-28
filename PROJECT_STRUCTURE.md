# 项目结构说明

## 目录组织

### 前端代码 (UI)
- **`client/`** - React 前端应用
  - `src/` - React 源代码
  - `public/` - 静态资源
  - `package.json` - 前端依赖管理

### 后端代码
- **`server/`** - Python 后端服务
  - `api/` - API 路由
  - `services/` - 业务逻辑服务
  - `utils/` - 工具函数
  - `logs/` - 日志文件
  - `requirements.txt` - Python 依赖
  - `main.py` - 主程序入口 (FastAPI)

### 根目录文件
- **`env.example`** - 环境变量模板
- **主启动脚本** - `start.sh`, `start.bat` (启动前后端)
- **主停止脚本** - `stop.sh`, `stop.bat` (停止前后端)
- **单独启动脚本** - `start-client.sh/bat`, `start-server.sh/bat`
- **单独停止脚本** - `stop-client.sh/bat`, `stop-server.sh/bat`
- **文档文件** - `README.md`, `API_DOCUMENTATION.md`, `USAGE.md`, `PROJECT_STRUCTURE.md` 等

## 代码分离原则

✅ **前端代码** 仅放在 `client/` 目录下
✅ **Python 后端代码** 仅放在 `server/` 目录下
✅ **日志文件** 统一放在 `server/logs/` 目录下
✅ **Python 依赖** 通过 `server/requirements.txt` 管理
✅ **前端依赖** 通过 `client/package.json` 管理
✅ **启动/停止脚本** 各自在对应目录下，根目录脚本调用子目录脚本

## 启动方式

#### 同时启动前后端（推荐）
```bash
./start.sh          # Linux/Mac
start.bat           # Windows
```

#### 单独启动
```bash
# 仅启动前端
./start-client.sh   # Linux/Mac
start-client.bat    # Windows

# 仅启动后端
./start-server.sh   # Linux/Mac
start-server.bat    # Windows
```

#### 直接调用子目录脚本
```bash
# 直接调用前端脚本
cd client && ./start.sh

# 直接调用后端脚本
cd server && ./start.sh
```

## 停止服务

#### 停止所有服务（推荐）
```bash
./stop.sh              # Linux/Mac
stop.bat               # Windows
```

#### 单独停止服务
```bash
# 仅停止前端
./stop-client.sh       # Linux/Mac
stop-client.bat        # Windows

# 仅停止后端
./stop-server.sh       # Linux/Mac
stop-server.bat        # Windows
```

#### 直接调用子目录停止脚本
```bash
# 直接调用前端停止脚本
cd client && ./stop.sh

# 直接调用后端停止脚本
cd server && ./stop.sh
```

## 注意事项

1. **环境变量**: 复制 `env.example` 到 `.env` 并配置 API 密钥
2. **日志**: 所有日志文件现在统一存储在 `server/logs/` 目录
3. **依赖管理**: 
   - 前端依赖: `cd client && npm install`
   - Python 依赖: `cd server && pip install -r requirements.txt`
4. **代码组织**: 严格遵循前端代码在 `client/`，Python 代码在 `server/` 的原则
5. **端口配置**: 
   - 前端: http://localhost:3000
   - 后端: http://localhost:3001
