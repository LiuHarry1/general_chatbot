#!/bin/bash

# 测试运行脚本
echo "🧪 开始运行测试..."

# 安装测试依赖
echo "📦 安装测试依赖..."
pip install -r tests/requirements.txt

# 运行所有测试
echo "▶️  运行所有测试..."
pytest tests/ -v

# 运行特定类型的测试
echo "🔍 运行单元测试..."
pytest tests/ -m unit -v

echo "🌐 运行API测试..."
pytest tests/ -m api -v

echo "⚙️  运行配置测试..."
pytest tests/test_config.py -v

echo "✅ 测试完成！"
