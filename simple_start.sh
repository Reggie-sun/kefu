#!/bin/bash

# Simple Start Script - 最简单的启动方式
echo "🚀 ChatGPT-on-WeChat Quick Start"
echo "=================================="

ROOT_DIR="/home/reggie/vscode_folder/chatgpt-on-wechat/chatgpt-on-wechat"

# 启动最基础的 Gateway（从项目根目录启动，保证能找到 gateway 包）
cd "$ROOT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.7+ first"
    exit 1
fi

# 安装 FastAPI 和 uvicorn
pip3 install --user fastapi uvicorn > /dev/null 2>&1

# 确保项目在 Python 路径中
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

# 启动服务
echo "📍 Starting Gateway API on http://localhost:8000"
python3 -m uvicorn gateway.app:app --host 0.0.0.0 --port 8000 &

# 等待服务启动
sleep 3

# 尝试打开浏览器
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000
elif command -v open &> /dev/null; then
    open http://localhost:8000
else
    echo "🌐 Please open http://localhost:8000 in your browser"
fi

echo ""
echo "✅ Server started!"
echo "📍 API endpoint: http://localhost:8000"
echo "📚 Press Ctrl+C to stop the server"
wait

# 停止服务
echo ""
echo "🛑 Stopping server..."
pkill -f "uvicorn app:app"
echo "✅ Server stopped"
