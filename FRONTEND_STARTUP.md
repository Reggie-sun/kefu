# 前端启动指南

## 🚀 快速启动

### 方法一：使用一键启动脚本（推荐）

```bash
cd /home/reggie/vscode_folder/chatgpt-on-wechat/chatgpt-on-wechat
./start_frontend.sh start
```

这将启动：
- ✅ Gateway API 服务器 (端口 8000)
- ✅ Dashboard 监控面板 (端口 3000)
- ✅ WeChat 智能机器人（如果配置了）

### 方法二：分别启动服务

#### 1. 启动 Gateway API
```bash
cd gateway
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 启动 Dashboard（可选）
```bash
cd dashboard
python3 app.py  # 或使用 uvicorn:app:app --port 3000
```

#### 3. 启动微信机器人（可选）
```bash
cd bot/smart_gateway
python smart_gateway_bot.py
```

### 方法三：使用 Docker 启动

```bash
# 在项目根目录
docker-compose up -d
```

## 📋 启动选项

| 命令 | 说明 |
|-------|-------|
| `./start_frontend.sh start` | 启动所有服务 |
| `./start_frontend.sh stop` | 停止所有服务 |
| `./start_frontend.sh status` | 查看服务状态 |
| `./start_frontend.sh test` | 测试服务并打开 Dashboard |
| `./start_frontend.sh gateway` | 只启动 Gateway API |
| `./start_frontend.sh dashboard` | 只启动 Dashboard |
| `./start_frontend.sh bot` | 只启动微信机器人 |
| `./start_frontend.sh rag` | 启动时集成 RAG 服务 |

## 🔧 配置选项

### 启用增强功能

在启动时设置环境变量：

```bash
# 启用业务工具系统
export USE_ENHANCED_TOOLS=true

# 启用增强检索（需要 RAG 服务）
export USE_ENHANCED_RETRIEVAL=true
export RAG_ENDPOINT=http://localhost:8001

# 启用工具缓存
export TOOL_CACHE_ENABLED=true

# 调试模式
export BUSINESS_TOOLS_DEBUG=true
```

### 配置文件位置

1. **机器人配置**：`bot/smart_gateway/config.json`
2. **环境变量**：`.env` 文件
3. **数据库配置**：通过环境变量设置

## 🌐 访问地址

启动成功后，可以访问：

- **Gateway API**：http://localhost:8000
  - API 文档：http://localhost:8000/docs
  - 健康检查：http://localhost:8000/healthz

- **Dashboard**：http://localhost:3000
  - 监控面板查看实时数据

- **RAG 服务**（如果启用）：http://localhost:8001
  - RAG API：http://localhost:8001/api/docs

## 🧪 测试 API

```bash
# 测试 Gateway API
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "test-session",
    "message": {
      "sender": "user",
      "receiver": "bot",
      "channel": "test",
      "message_type": "text",
      "content": "查询订单 ORD-202401001"
    },
    "tools_allowed": ["lookup_order", "check_logistics"],
    "metadata": {
      "use_enhanced_tools": true,
      "use_enhanced_retrieval": true
    }
  }'
```

## 📊 使用业务工具

### 1. 订单查询
```json
{
  "message": {
    "content": "查询我的订单",
    "message_type": "text"
  },
  "tools_allowed": ["lookup_order"]
}
```

### 2. 物流跟踪
```json
{
  "message": {
    "content": "查询物流 SF1234567890",
    "message_type": "text"
  },
  "tools_allowed": ["check_logistics"]
}
```

### 3. 产品信息
```json
{
  "message": {
    "content": "查询智能手表信息",
    "message_type": "text"
  },
  "tools_allowed": ["product_info"]
}
```

### 4. 库存检查
```json
{
  "message": {
    "content": "检查库存 SKU-001,SKU-002",
    "message_type": "text"
  },
  "tools_allowed": ["check_inventory"]
}
```

### 5. 产品推荐
```json
{
  "message": {
    "content": "推荐一些智能手表",
    "message_type": "text"
  },
  "tools_allowed": ["get_product_recommendations"]
}
```

## 🔍 故障排查

### 1. 端口被占用
```bash
# 查看端口占用
lsof -i :8000
lsof -i :3000

# 杀死进程
kill -9 <PID>
```

### 2. 依赖问题
```bash
# 检查 Python 环境
python3 --version

# 安装依赖
pip3 install -r requirements.txt
```

### 3. 配置问题
```bash
# 检查配置文件
ls -la config.json

# 复制模板配置
cp config-template.json config.json
```

## 📚 开发指南

### 添加新的业务工具

1. 在 `gateway/business_tools.py` 中添加新方法
2. 在 `gateway/enhanced_tools.py` 的 `_get_tool_intent` 中添加关键词
3. 在 `docs/BUSINESS_TOOLS_GUIDE.md` 中更新文档

### 调试模式

启用调试日志：

```bash
export BUSINESS_TOOLS_DEBUG=true
./start_frontend.sh start
```

## 💡 提示

1. **首次启动**：建议先测试基础功能
2. **性能优化**：使用缓存减少数据库查询
3. **监控日志**：关注 API 响应时间
4. **数据安全**：生产环境请使用真实的数据库连接

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！