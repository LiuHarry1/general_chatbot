#!/bin/bash

# 设置环境变量并启动服务器
export DASHSCOPE_API_KEY="sk-f256c03643e9491fb1ebc278dd958c2d"
export TAVILY_API_KEY=""
export PORT="3002"
export DEBUG="true"

echo "🚀 启动AI聊天机器人服务器..."
echo "API密钥: ${DASHSCOPE_API_KEY:0:10}..."
echo "端口: $PORT"
echo "调试模式: $DEBUG"

cd server && python main.py
