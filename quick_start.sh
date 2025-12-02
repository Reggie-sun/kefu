#!/bin/bash

# Quick Start Script - 最简单的启动方式
# 即使没有任何配置，也能运行基础功能

echo "🚀 ChatGPT-on-WeChat Quick Start"
echo "=================================="

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.7+ first"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# 安装基础依赖
echo "📦 Installing basic dependencies..."
pip3 install --user fastapi uvicorn &> /dev/null

# 检查是否存在配置文件
if [ ! -f "config.json" ]; then
    echo "⚠️  config.json not found, using default configuration"
fi

# 设置默认配置
export GATEWAY_LOG_DB="sqlite:///tmp/gateway_logs.sqlite3"
export USE_SIMPLE_TOOLS="true"  # 使用简单工具作为后备

echo ""
echo "🎯 Starting services..."

# 启动 Gateway API
echo "📍 Starting Gateway API on http://localhost:8000"
cd gateway
cat > gateway_simple.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn
import json

app = FastAPI(title="ChatGPT-on-WeChat", version="1.0.0")

class ChatMessage(BaseModel):
    content: str

@app.get("/")
def read_root():
    return HTMLResponse("""
        <h1>✨ ChatGPT-on-WeChat API</h1>
        <h2>🚀 Server is running!</h2>
        <p>Try the chat endpoint:</p>
        <form method="post" action="/chat" style="margin: 20px; padding: 20px; border: 1px solid #ccc; border-radius: 5px; display: inline-block;">
            <input type="text" name="content" placeholder="Type your message..." style="width: 300px; padding: 10px;" required>
            <button type="submit" style="padding: 10px 20px; background: #0ea5e9; color: white; border: none; border-radius: 5px; cursor: pointer;">Send</button>
        </form>
        <h3>API Documentation:</h3>
        <p>Visit <a href="/docs" target="_blank">API Docs</a> for detailed API information.</p>
    """)

@app.post("/chat")
async def chat(message: ChatMessage):
    # Simple response
    response = {
        "reply": f"You said: {message.content}",
        "timestamp": "2024-01-01 12:00:00",
        "session_id": "demo-session"
    }
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# 启动 Gateway
echo "📍 Starting Gateway API on http://localhost:8000"
cd gateway
python3 gateway_simple.py &

# 等待一下启动
sleep 3

# 等待一下启动
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
echo "✅ Quick start completed!"
echo ""
echo "📖 For full features:"
echo "   • Run: ./start_frontend.sh start"
echo "   • Read: FRONTEND_STARTUP.md"
echo ""
echo "🛠️  Need help?"
echo "   • Check logs: docker logs gateway"
echo "   • View docs: http://localhost:8000/docs"
echo ""