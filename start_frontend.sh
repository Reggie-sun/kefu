#!/bin/bash

# Frontend Start Script - 一键启动完整的前端系统
# ========================================================

echo "🚀 Starting ChatGPT-on-WeChat Frontend System..."
echo "================================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# 确保项目根目录在 Python 路径中，避免模块导入失败
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${2}${1}${NC}"
}

# 检查 Python 环境
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_message "✅ Python 3 found: $PYTHON_VERSION"
    else
        print_message "❌ Python 3 not found!"
        print_message "Please install Python 3.7 or higher"
        exit 1
    fi
}

# 检查并安装依赖
install_dependencies() {
    print_message "📦 Checking and installing dependencies..."

    # 检查 pip
    if ! command -v pip &> /dev/null; then
        print_message "❌ pip not found!"
        print_message "Please install pip first"
        exit 1
    fi

    # 安装 FastAPI
    if ! python3 -c "import fastapi" &> /dev/null 2>&1; then
        print_message "Installing FastAPI..."
        pip3 install fastapi -q
    fi

    # 兼容 Python 3.13 删除的 cgi 模块，web.py 依赖它
    if ! python3 -c "import cgi" &> /dev/null 2>&1; then
        print_message "Installing legacy-cgi for Python 3.13 compatibility..."
        pip3 install legacy-cgi -q
    fi

    # 安装 uvicorn
    if ! python3 -c "import uvicorn" &> /dev/null 2>&1; then
        print_message "Installing uvicorn..."
        pip3 install uvicorn -q
    fi

    # 安装其他依赖
    if [ -f "requirements.txt" ]; then
        print_message "Installing requirements from requirements.txt..."
        PIP_NO_BUILD_ISOLATION=1 pip3 install -r requirements.txt -q
    fi

    print_message "✅ Dependencies installed!"
}

# 启动 Gateway API
start_gateway() {
    print_message "🔧 Starting Gateway API Server..."

    # 设置环境变量
    export GATEWAY_LOG_DB="sqlite:///tmp/gateway_logs.sqlite3"
    export USE_ENHANCED_TOOLS=true
    export USE_ENHANCED_RETRIEVAL=true

    # 启动服务器
    cd gateway
    if [ -f "app.py" ]; then
        python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
        GATEWAY_PID=$!
        echo $GATEWAY_PID > /tmp/gateway.pid
        print_message "✅ Gateway API started on http://localhost:8000"
        print_message "   PID: $GATEWAY_PID"
    else
        print_message "❌ Gateway app.py not found!"
        return 1
    fi

    cd ..
}

# 启动 Dashboard
start_dashboard() {
    print_message "📊 Starting Dashboard..."

    cd dashboard
    if [ -f "app.py" ]; then
        python3 -m uvicorn app:app --host 0.0.0.0 --port 3000 --reload &
        DASHBOARD_PID=$!
        echo $DASHBOARD_PID > /tmp/dashboard.pid
        print_message "✅ Dashboard started on http://localhost:3000"
        print_message "   PID: $DASHBOARD_PID"
    else
        print_message "❌ Dashboard app.py not found!"
        return 1
    fi

    cd ..
}

# 启动 Smart Gateway Bot (微信）
start_wechat_bot() {
    print_message "🤖 Starting WeChat Bot..."

    # 检查是否有微信机器人配置
    if [ -f "config.json" ] || [ -f "config-template.json" ]; then
        cd bot
        if [ -f "smart_gateway/smart_gateway_bot.py" ]; then
            python3 smart_gateway/smart_gateway_bot.py &
            BOT_PID=$!
            echo $BOT_PID > /tmp/wechat_bot.pid
            print_message "✅ WeChat Bot started"
            print_message "   PID: $BOT_PID"
            print_message "   Configuration: Using config.json or config-template.json"
        else
            print_message "❌ Smart Gateway Bot not found!"
        fi
        cd ..
    else
        print_message "⚠️  No configuration found for WeChat Bot"
        print_message "   Please ensure config.json exists"
    fi
}

# 检查 RAG 服务
check_rag_service() {
    RAG_DIR="/home/reggie/vscode_folder/RAG"
    if [ -d "$RAG_DIR" ]; then
        print_message "🔍 RAG Service detected at $RAG_DIR"
        print_message "   To enable RAG integration, run:"
        print_message "   cd $RAG_DIR/rag-system/backend && python main.py"
        print_message ""
        print_message "   Or use the integrated start script:"
        print_message "   ./start_with_rag.sh"
    else
        print_message "ℹ️  RAG Service not found"
    fi
}

# 等待服务启动
wait_for_services() {
    print_message ""
    print_message "⏳ Waiting for services to be ready..."

    # 等待 Gateway API
    echo -n "   Checking Gateway API..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/healthz &> /dev/null; then
            print_message " ✅ Gateway API is ready!"
            break
        fi
        echo -n "."
        sleep 1
    done

    # 等待 Dashboard
    echo -n "   Checking Dashboard..."
    for i in {1..10}; do
        if curl -s http://localhost:3000 &> /dev/null; then
            print_message " ✅ Dashboard is ready!"
            break
        fi
        echo -n "."
        sleep 1
    done
}

# 显示服务状态
show_status() {
    echo ""
    print_message "📊 Service Status:"
    echo "================================"

    # Gateway API
    if [ -f "/tmp/gateway.pid" ]; then
        GATEWAY_PID=$(cat /tmp/gateway.pid)
        if ps -p $GATEWAY_PID > /dev/null; then
            print_message "✅ Gateway API: Running (PID: $GATEWAY_PID)"
            print_message "   URL: http://localhost:8000"
            print_message "   Health: http://localhost:8000/healthz"
        else
            print_message "❌ Gateway API: Not running"
        fi
    else
        print_message "❌ Gateway API: Not started"
    fi

    # Dashboard
    if [ -f "/tmp/dashboard.pid" ]; then
        DASHBOARD_PID=$(cat /tmp/dashboard.pid)
        if ps -p $DASHBOARD_PID > /dev/null; then
            print_message "✅ Dashboard: Running (PID: $DASHBOARD_PID)"
            print_message "   URL: http://localhost:3000"
        else
            print_message "❌ Dashboard: Not running"
        fi
    else
        print_message "❌ Dashboard: Not started"
    fi

    # WeChat Bot
    if [ -f "/tmp/wechat_bot.pid" ]; then
        BOT_PID=$(cat /tmp/wechat_bot.pid)
        if ps -p $BOT_PID > /dev/null; then
            print_message "✅ WeChat Bot: Running (PID: $BOT_PID)"
        else
            print_message "❌ WeChat Bot: Not running"
        fi
    else
        print_message "❌ WeChat Bot: Not started"
    fi

    echo "================================"
}

# 停止所有服务
stop_services() {
    print_message ""
    print_message "🛑 Stopping all services..."

    # 停止 Gateway API
    if [ -f "/tmp/gateway.pid" ]; then
        GATEWAY_PID=$(cat /tmp/gateway.pid)
        if ps -p $GATEWAY_PID > /dev/null; then
            print_message "🛑 Stopping Gateway API (PID: $GATEWAY_PID)..."
            kill $GATEWAY_PID
            rm /tmp/gateway.pid
        fi
    fi

    # 停止 Dashboard
    if [ -f "/tmp/dashboard.pid" ]; then
        DASHBOARD_PID=$(cat /tmp/dashboard.pid)
        if ps -p $DASHBOARD_PID > /dev/null; then
            print_message "🛑 Stopping Dashboard (PID: $DASHBOARD_PID)..."
            kill $DASHBOARD_PID
            rm /tmp/dashboard.pid
        fi
    fi

    # 停止 WeChat Bot
    if [ -f "/tmp/wechat_bot.pid" ]; then
        BOT_PID=$(cat /tmp/wechat_bot.pid)
        if ps -p $BOT_PID > /dev/null; then
            print_message "🛑 Stopping WeChat Bot (PID: $BOT_PID)..."
            kill $BOT_PID
            rm /tmp/wechat_bot.pid
        fi
    fi

    print_message "✅ All services stopped!"
}

# 测试服务
test_services() {
    print_message ""
    print_message "🧪 Testing services..."

    # 测试 Gateway API
    echo "Testing Gateway API..."
    curl -X POST http://localhost:8000/chat \
        -H "Content-Type: application/json" \
        -d '{
            "session_id": "test-session",
            "message": {
                "sender": "test",
                "receiver": "bot",
                "channel": "test",
                "message_type": "text",
                "content": "查询订单 ORD-202401001"
            },
            "tools_allowed": ["lookup_order"],
            "metadata": {
                "use_enhanced_tools": true,
                "use_enhanced_retrieval": true
            }
        }' | python3 -m json.tool

    echo ""

    # 测试 Dashboard
    echo "Opening Dashboard in browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    elif command -v open &> /dev/null; then
        open http://localhost:3000
    else
        echo "Please open http://localhost:3000 in your browser"
    fi
}

# 显示帮助
show_help() {
    echo ""
    print_message "📚 ChatGPT-on-WeChat Frontend System"
    echo "================================"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start       Start all services (Gateway, Dashboard, WeChat Bot)"
    echo "  stop        Stop all services"
    echo "  status      Show service status"
    echo "  test        Test services and open dashboard"
    echo "  gateway     Start only Gateway API"
    echo "  dashboard   Start only Dashboard"
    echo "  bot         Start only WeChat Bot"
    echo "  rag         Start with RAG integration"
    echo "  help        Show this help message"
    echo ""
    echo "Service URLs:"
    echo "  • Gateway API:    http://localhost:8000"
    echo "  • Dashboard:      http://localhost:3000"
    echo "  • API Docs:       http://localhost:8000/docs"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 test                    # Test and open dashboard"
    echo "  USE_ENHANCED_TOOLS=true $0 start  # Start with enhanced tools"
    echo ""
    echo "Environment Variables:"
    echo "  • USE_ENHANCED_TOOLS=true     # Enable enhanced business tools"
    echo "  • USE_ENHANCED_RETRIEVAL=true # Enable enhanced retrieval"
    echo "  • RAG_ENDPOINT=http://...     # RAG service endpoint (optional)"
}

# 主逻辑
main() {
    case "${1:-}" in
        start)
            check_python
            install_dependencies
            start_gateway
            start_dashboard
            start_wechat_bot
            wait_for_services
            show_status
            print_message ""
            print_message "🎉 All services started successfully!"
            print_message ""
            print_message "📋 Next steps:"
            print_message "  1. Open Dashboard: http://localhost:3000"
            print_message "  2. View API docs: http://localhost:8000/docs"
            print_message "  3. Test with: $0 test"
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
            ;;
        test)
            test_services
            ;;
        gateway)
            check_python
            install_dependencies
            start_gateway
            ;;
        dashboard)
            check_python
            install_dependencies
            start_dashboard
            ;;
        bot)
            check_python
            install_dependencies
            start_wechat_bot
            ;;
        rag)
            # 使用 RAG 集成启动脚本
            if [ -f "start_with_rag.sh" ]; then
                ./start_with_rag.sh
            else
                print_message "❌ start_with_rag.sh not found!"
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            # 默认启动所有服务
            main start
            ;;
        *)
            print_message "❌ Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# 捕获中断信号
trap 'print_message "\n🛑 Interrupted. Stopping services..."; stop_services; exit 1' INT TERM

# 运行主函数
main "$@"
