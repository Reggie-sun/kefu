# 🚀 ChatGPT-on-WeChat 部署指南

## 📋 部署方案概览

本系统提供多种部署方式，从简单到复杂，满足不同场景需求：

### 方案一：Docker Compose 一键部署（推荐）

**适合**：生产环境、快速部署

```bash
# 克隆项目
git clone <repository-url>
cd chatgpt-on-wechat

# 启动所有服务
docker-compose -f docker-compose.full.yml up -d
```

**包含服务**：
- ✅ Gateway API (端口 8000)
- ✅ Dashboard 监控面板 (端口 3000)
- ✅ MongoDB 数据库
- ✅ Redis 缓存
- ✅ WeChat 智能机器人
- ✅ RAG 检索服务（可选）
- ✅ Nginx 反向代理

### 方案二：本地开发部署

**适合**：开发、测试环境

```bash
# 1. 安装依赖
pip3 install -r requirements.txt
pip3 install -r gateway/requirements.txt
pip3 install -r bot/requirements.txt

# 2. 配置环境变量
cp config-template.json config.json
# 编辑 config.json 添加必要的配置

# 3. 启动服务

# 启动 Gateway API
cd gateway
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 启动 Dashboard
cd dashboard
python3 app.py

# 启动微信机器人
cd bot/smart_gateway
python smart_gateway_bot.py
```

### 方案三：混合部署

**适合**：已有基础设施，需要集成

```yaml
# docker-compose.yml - 核心服务
version: '3.8'
services:
  mongodb:
    image: mongo:7
  redis:
    image: redis:7-alpine
  gateway:
    build: ./gateway
    environment:
      - GATEWAY_LOG_DB=${YOUR_MONGODB_URL}
      - REDIS_URL=${YOUR_REDIS_URL}
```

## 🔧 环境配置

### 必需配置

1. **微信机器人配置**
```bash
# 复制配置模板
cp bot/smart_gateway/config-template.json bot/smart_gateway/config.json

# 编辑配置
vim bot/smart_gateway/config.json
```

配置项：
```json
{
  "wechat": {
    "app_id": "你的微信AppID",
    "app_secret": "你的微信AppSecret",
    "token": "你的微信Token",
    "encoding_aes_key": "AES加密密钥"
  },
  "gateway": {
    "api_url": "http://localhost:8000",
    "timeout": 30
  }
}
```

2. **数据库配置**
```bash
# MongoDB
export GATEWAY_LOG_DB="mongodb://username:password@localhost:27017/chatgpt"

# Redis（可选）
export REDIS_URL="redis://:password@localhost:6379/0"
```

3. **RAG 服务配置**
```bash
# 启用 RAG 集成
export USE_ENHANCED_RETRIEVAL=true
export RAG_ENDPOINT=http://localhost:8001
```

## 🐳 Docker 部署详细步骤

### 1. 准备工作

```bash
# 创建必要目录
mkdir -p logs config bot/config bot/logs rag-data rag-models

# 设置权限
chmod 755 bot/config
```

### 2. 构建镜像

```bash
# 构建 Gateway
docker build -t chatgpt-gateway ./gateway

# 构建 Dashboard
docker build -t chatgpt-dashboard ./dashboard

# 构建微信机器人
docker build -t chatgpt-bot ./bot/smart_gateway
```

### 3. 启动服务

```bash
# 使用完整配置启动
docker-compose -f docker-compose.full.yml up -d

# 查看服务状态
docker-compose -f docker-compose.full.yml ps

# 查看日志
docker-compose -f docker-compose.full.yml logs -f gateway
```

### 4. 配置 Nginx（生产环境）

```nginx
# 创建 Nginx 配置
mkdir -p nginx
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream gateway {
        server gateway:8000;
    }

    upstream dashboard {
        server dashboard:3000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # API 路由
        location /api/ {
            proxy_pass http://gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Dashboard 路由
        location / {
            proxy_pass http://dashboard;
            proxy_set_header Host $host;
        }

        # WebSocket 支持
        location /ws {
            proxy_pass http://gateway;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF

# 启动 Nginx
docker run -d -p 80:80 -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf nginx:alpine
```

## 🔍 健康检查

### API 端点

```bash
# Gateway 健康检查
curl http://localhost:8000/healthz

# 返回示例
{
  "status": "ok",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 服务依赖关系

```mermaid
graph TD
    A[用户请求] --> B[Nginx]
    B --> C{Gateway API}
    B --> D[Dashboard]
    C --> E[MongoDB]
    C --> F[Redis]
    C --> G[RAG Service]
    C --> H[WeChat API]

    E --> I[Logging Store]
    F --> J[Session Cache]
    G --> K[Vector DB]
```

## 📊 监控指标

### 关键指标

1. **API 响应时间**
   - 目标：P95 < 800ms
   - 监控：Gateway 健康检查

2. **系统资源**
   - CPU 使用率
   - 内存使用率
   - 磁盘空间

3. **业务指标**
   - 消息处理速率
   - 工具调用成功率
   - 知识库命中率

### 监控命令

```bash
# Docker 资源使用
docker stats

# 服务状态
docker-compose ps

# 实时日志
docker-compose logs -f gateway --tail=100
```

## 🔒 安全配置

### 1. 网络安全

```yaml
# 防火墙配置
ufw allow 8000/tcp  # Gateway API
ufw allow 3000/tcp  # Dashboard
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# IP 白名单（可选）
export ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8"
```

### 2. 认证授权

```yaml
# API 密钥
export API_SECRET_KEY="your-secret-key-here"

# JWT 配置
export JWT_SECRET_KEY="your-jwt-secret"
export JWT_EXPIRE_HOURS=24
```

## 🚨 故障排查

### 常见问题

1. **端口被占用**
```bash
# 查找占用进程
lsof -i :8000

# 杀死进程
kill -9 $(lsof -t -i :8000)
```

2. **数据库连接失败**
```bash
# 检查 MongoDB
docker exec -it chatgpt-mongodb mongo --eval "db.adminCommand('ismaster')"

# 检查连接
docker exec -it chatgpt-gateway python -c "
from gateway.logging_store import LoggingStore
import os
try:
    store = LoggingStore(os.environ.get('GATEWAY_LOG_DB'))
    print('数据库连接成功')
except Exception as e:
    print(f'数据库连接失败: {e}')
"
```

3. **微信机器人无响应**
```bash
# 检查日志
docker-compose logs -f wechat-bot

# 测试 API
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"test","message":{"content":"test"}}'
```

## 📚 API 文档

### 完整 API 文档

访问地址：http://localhost:8000/docs

包含：
- `/chat` - 聊天接口
- `/healthz` - 健康检查
- `/tools/lookup_order` - 订单查询
- `/tools/check_logistics` - 物流跟踪
- 等...

## 🔄 更新和维护

### 自动更新脚本

```bash
#!/bin/bash
# update.sh
git pull origin main
docker-compose -f docker-compose.full.yml pull
docker-compose -f docker-compose.full.yml up -d --force-recreate
```

### 备份策略

1. **数据备份**
```bash
# MongoDB
docker exec chatgpt-mongodb mongodump --out /backup/mongodb-$(date +%Y%m%d).gz

# 配置文件
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/ bot/config/
```

2. **恢复操作**
```bash
# 恢复配置
tar -xzf config-backup-20240101.tar.gz

# 恢复数据库
docker exec -i chatgpt-mongodb mongorestore /backup/mongodb-20240101.gz
```

## 📈 性能优化建议

### 1. 数据库优化
- 使用 MongoDB 索引
- 配置连接池
- 启用查询缓存

### 2. 缓存策略
- Redis 缓存热点数据
- CDN 缓存静态资源
- 应用层缓存

### 3. 代码优化
- 异步处理
- 批量操作
- 连接复用

## 🎯 生产环境检查清单

- [ ] 配置环境变量
- [ ] 设置域名和 SSL
- [ ] 配置监控告警
- [ ] 设置日志轮转
- [ ] 配置备份策略
- [ ] 性能压测
- [ ] 安全扫描

## 🤝 获取帮助

如果遇到问题，请：

1. 查看日志文件
2. 访问 GitHub Issues
3. 查看文档
4. 联系技术支持

---

**部署成功后，你的系统就 ready 了！** 🎉