#!/usr/bin/env bash
# 一键启动 Gateway + Dashboard + WeChatMP Bot
# 默认端口：Gateway 8500，Dashboard 3000，Bot 8080。可通过 BACKEND_PORT/FRONTEND_PORT/BOT_PORT 覆盖。
export CUSTOMER_SERVICE_API_BASE_URL=https://api.srj666.com   # 你的 RAG 外网域名
export CUSTOMER_SERVICE_API_TOKEN=yuzhouwudichaojibaolongzhanshensrj   # 与 RAG 端配置一致
export CUSTOMER_SERVICE_API_TIMEOUT=60
export EXTERNAL_RAG_ONLY=true
# 提高网关调用超时，避免外部RAG较慢导致15s超时
export smart_gateway_timeout=60
# 本地联调时默认启用 Smart Gateway
export smart_gateway_enabled=true
# 如需固定出口 IP（走代理），设置 WECHAT_HTTP_PROXY，例如 http://127.0.0.1:7897
if [[ -n "${WECHAT_HTTP_PROXY:-}" ]]; then
  export http_proxy="$WECHAT_HTTP_PROXY"
  export https_proxy="$WECHAT_HTTP_PROXY"
  export HTTP_PROXY="$WECHAT_HTTP_PROXY"
  export HTTPS_PROXY="$WECHAT_HTTP_PROXY"
  export ALL_PROXY="${WECHAT_ALL_PROXY:-}"
  export all_proxy="${WECHAT_ALL_PROXY:-}"
  export no_proxy="${WECHAT_NO_PROXY:-localhost,127.0.0.1}"
  export NO_PROXY="$no_proxy"
else
  unset http_proxy HTTP_PROXY https_proxy HTTPS_PROXY ALL_PROXY all_proxy
fi

set -euo pipefail

# 激活 kefu conda 环境（若可用）
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate kefu >/dev/null 2>&1 || true
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8500}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BOT_PORT="${BOT_PORT:-8080}"
PYTHON_BIN="${PYTHON_BIN:-python}"
RELOAD="${RELOAD:-false}"

# Customer-service RAG defaults（可在运行前覆盖）
export CUSTOMER_SERVICE_API_BASE_URL="${CUSTOMER_SERVICE_API_BASE_URL:-https://api.srj666.com}"
export CUSTOMER_SERVICE_API_TOKEN="${CUSTOMER_SERVICE_API_TOKEN:-yuzhouwudichaojibaolongzhanshensrj}"
export CUSTOMER_SERVICE_API_TIMEOUT="${CUSTOMER_SERVICE_API_TIMEOUT:-60}"

# 确保项目在 Python 路径中
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

# PID 文件
GATEWAY_PID_FILE="$ROOT_DIR/.tmp_gateway.pid"
DASHBOARD_PID_FILE="$ROOT_DIR/.tmp_dashboard.pid"
BOT_PID_FILE="$ROOT_DIR/.tmp_bot.pid"

cleanup() {
  for pid_file in "$GATEWAY_PID_FILE" "$DASHBOARD_PID_FILE" "$BOT_PID_FILE"; do
    if [[ -f "$pid_file" ]]; then
      kill "$(cat "$pid_file")" 2>/dev/null || true
      rm -f "$pid_file"
    fi
  done
}
trap cleanup EXIT

kill_old() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      echo "🧹 清理旧进程 PID=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$pid_file"
  fi
}

free_port() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    echo "ℹ️ 未找到 lsof，无法自动释放端口 $port，如启动失败请手动检查。"
    return
  fi
  for attempt in {1..5}; do
    pids=$(lsof -ti :"$port" || true)
    if [[ -z "$pids" ]]; then return; fi
    echo "🧹 端口 $port 被占用，正在释放: $pids (尝试 $attempt)"
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -ti :"$port" || true)
    if [[ -n "$pids" ]]; then kill -9 $pids 2>/dev/null || true; fi
    sleep 1
  done
  pids=$(lsof -ti :"$port" || true)
  if [[ -n "$pids" ]]; then
    echo "❌ 无法释放端口 $port，仍被占用: $pids"
    exit 1
  fi
}

start_gateway() {
  echo "🚀 启动 Gateway 后端，端口: $BACKEND_PORT"
  kill_old "$GATEWAY_PID_FILE"
  free_port "$BACKEND_PORT"
  cd "$ROOT_DIR"
  export GATEWAY_LOG_DB="sqlite:///${ROOT_DIR}/tmp/gateway_logs.sqlite3"
  export USE_ENHANCED_TOOLS=true
  export USE_ENHANCED_RETRIEVAL=true
  local reload_flag=()
  [[ "$RELOAD" == "true" ]] && reload_flag=(--reload)
  "$PYTHON_BIN" -m uvicorn gateway.app:app --host 0.0.0.0 --port "$BACKEND_PORT" "${reload_flag[@]}" &
  echo $! > "$GATEWAY_PID_FILE"
}

start_dashboard() {
  echo "📊 启动 Dashboard 前端，端口: $FRONTEND_PORT"
  kill_old "$DASHBOARD_PID_FILE"
  free_port "$FRONTEND_PORT"
  cd "$ROOT_DIR/dashboard"
  local reload_flag=()
  [[ "$RELOAD" == "true" ]] && reload_flag=(--reload)
  "$PYTHON_BIN" -m uvicorn app:app --host 0.0.0.0 --port "$FRONTEND_PORT" "${reload_flag[@]}" &
  echo $! > "$DASHBOARD_PID_FILE"
}

start_bot() {
  echo "🤖 启动 WeChatMP Bot，端口: $BOT_PORT"
  kill_old "$BOT_PID_FILE"
  free_port "$BOT_PORT"
  cd "$ROOT_DIR"
  "$PYTHON_BIN" app.py &
  echo $! > "$BOT_PID_FILE"
}

wait_ready() {
  local url="$1"
  for _ in {1..20}; do
    if curl -sf "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

start_gateway
start_dashboard
start_bot

if wait_ready "http://127.0.0.1:${BACKEND_PORT}/healthz"; then
  echo "✅ Gateway 就绪: http://127.0.0.1:${BACKEND_PORT}"
else
  echo "⚠️ 未检测到 Gateway 健康响应"
fi

if wait_ready "http://127.0.0.1:${FRONTEND_PORT}"; then
  echo "✅ Dashboard 就绪: http://127.0.0.1:${FRONTEND_PORT}"
else
  echo "⚠️ 未检测到 Dashboard 响应"
fi

echo "按 Ctrl+C 停止服务（会自动清理后台进程）"
wait
