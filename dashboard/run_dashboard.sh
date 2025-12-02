#!/bin/bash

# AI 工作台启动脚本

echo "正在启动 AI 工作台..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3.7+"
    exit 1
fi

# 检查并安装依赖
echo "检查依赖..."
pip install -q fastapi uvicorn python-multipart 2>/dev/null

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 启动服务器
echo "启动服务器在 http://localhost:8000"
echo "按 Ctrl+C 停止服务器"
cd "$DIR"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload