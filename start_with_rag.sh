#!/bin/bash

# Start script for ChatGPT-on-WeChat with RAG integration
# ==================================================

echo "🚀 Starting ChatGPT-on-WeChat with RAG integration..."

# Check if RAG service is available
RAG_DIR="/home/reggie/vscode_folder/RAG"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables
if [ -f ".env" ]; then
    echo "✅ Loading .env configuration"
    export $(grep -v '^#' .env | xargs)
fi

if [ -f ".env.rag" ]; then
    echo "✅ Loading RAG configuration from .env.rag"
    export $(grep -v '^#' .env.rag | xargs)
fi

# Function to check if service is running
check_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1

    echo "⏳ Checking $name availability..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✅ $name is ready!"
            return 0
        fi
        echo "⏳ Attempt $attempt/$max_attempts: $name not ready yet..."
        sleep 2
        ((attempt++))
    done

    echo "❌ $name failed to start"
    return 1
}

# Start RAG service if configured
if [ -n "$RAG_ENDPOINT" ] && [ -d "$RAG_DIR" ]; then
    echo "🔧 Starting RAG service..."

    # Navigate to RAG directory
    cd "$RAG_DIR/rag-system/backend"

    # Check if virtual environment exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -f "requirements.txt" ]; then
        echo "📦 Installing RAG dependencies..."
        pip install -r requirements.txt > /dev/null 2>&1
    fi

    # Start RAG service in background
    echo "🚀 Starting RAG service on port 8001..."
    python main.py > /tmp/rag_service.log 2>&1 &
    RAG_PID=$!

    # Wait for RAG service to be ready
    if check_service "http://localhost:8001/api/healthz" "RAG service"; then
        echo "✅ RAG service started successfully (PID: $RAG_PID)"
    else
        echo "❌ Failed to start RAG service, continuing with local retrieval only"
        export DISABLE_RAG_SERVICE=true
    fi

    # Return to original directory
    cd "$CURRENT_DIR"
else
    echo "ℹ️  RAG service not configured, using local retrieval only"
    export DISABLE_RAG_SERVICE=true
fi

# Start ChatGPT-on-WeChat services
echo "🔧 Starting ChatGPT-on-WeChat services..."

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    echo "🐳 Starting with Docker Compose..."

    # Set environment variables for docker-compose
    export RAG_ENDPOINT=${RAG_ENDPOINT:-}
    export RAG_API_KEY=${RAG_API_KEY:-}
    export RAG_DEFAULT_TOP_K=${RAG_DEFAULT_TOP_K:-5}
    export RAG_DEFAULT_THRESHOLD=${RAG_DEFAULT_THRESHOLD:-0.3}

    # Start services
    docker-compose up -d

    # Check if services are ready
    echo "⏳ Waiting for services to be ready..."
    sleep 10

    # Check Gateway
    if check_service "http://localhost:8000/healthz" "Gateway service"; then
        echo "✅ Gateway service is ready!"
    fi

    # Check Dashboard
    if check_service "http://localhost:3000" "Dashboard"; then
        echo "✅ Dashboard is ready!"
    fi

    echo ""
    echo "🎉 All services are running!"
    echo ""
    echo "📍 Service URLs:"
    echo "   • Gateway API: http://localhost:8000"
    echo "   • Dashboard:   http://localhost:3000"
    if [ -n "$RAG_ENDPOINT" ] && [ "$DISABLE_RAG_SERVICE" != "true" ]; then
        echo "   • RAG Service: $RAG_ENDPOINT"
    fi
    echo ""
    echo "📋 Useful commands:"
    echo "   • View logs:      docker-compose logs -f"
    echo "   • Stop services:  docker-compose down"
    echo "   • Restart:       ./start_with_rag.sh"
    echo ""
    echo "🔍 Testing the integration:"
    echo "   curl -X POST http://localhost:8000/chat \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{"
    echo "       \"session_id\": \"test-session\","
    echo "       \"message\": {"
    echo "         \"sender\": \"user\","
    echo "         \"receiver\": \"bot\","
    echo "         \"channel\": \"test\","
    echo "         \"message_type\": \"text\","
    echo "         \"content\": \"查询退款政策\""
    echo "       },"
    echo "       \"metadata\": {"
    echo "         \"use_enhanced_retrieval\": true"
    echo "       }"
    echo "     }'"

else
    echo "❌ Docker Compose not found. Please install Docker Compose or run services manually."
fi

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."

    # Kill RAG service if running
    if [ -n "$RAG_PID" ]; then
        echo "🛑 Stopping RAG service (PID: $RAG_PID)..."
        kill $RAG_PID 2>/dev/null
    fi

    # Stop Docker Compose services
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    fi

    echo "✅ All services stopped"
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Keep script running
echo "ℹ️  Press Ctrl+C to stop all services"
wait