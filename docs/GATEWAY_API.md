# Gateway API 路由说明

## 服务信息
- 默认监听：`http://localhost:8000`
- 健康检查：`/healthz`
- API 文档：`/docs`（Uvicorn + FastAPI 自动生成）

## 路由列表

### GET `/healthz`
- **用途**：健康检查，返回 `{"status": "ok"}`。
- **鉴权**：无。

### POST `/chat`
- **用途**：统一对话入口，将消息转发到检索 / 工具 / 模型链路。
- **鉴权**：无（如需可在网关层自行加鉴权）。
- **请求体（JSON）**：
  ```json
  {
    "session_id": "会话ID",
    "message": {
      "sender": "发送方ID",
      "receiver": "接收方ID",
      "channel": "渠道标识",
      "message_type": "text|voice|image|video|file|news|event.*",
      "content": "消息内容（可为空，语音/图片用 media_url）",
      "timestamp": 0,
      "metadata": {},
      "message_id": "可选",
      "media_url": "可选"
    },
    "tools_allowed": ["lookup_order", "check_logistics", "product_info"],
    "rag": {
      "top_k": 3,
      "threshold": 0.3
    },
    "trace_id": "可选",
    "metadata": {
      "use_enhanced_retrieval": true,
      "use_enhanced_tools": true,
      "rerank": false,
      "use_rag_first": true
    }
  }
  ```
- **响应体（JSON）**：
  ```json
  {
    "reply_text": "字符串回复",
    "kb_hit": true,
    "confidence": 0.92,
    "retrieved": [
      {"text": "命中文档", "score": 0.9, "metadata": {}, "doc_id": "doc-1"}
    ],
    "tool_traces": [],
    "tool_calls": [],
    "source_refs": [],
    "latency": {
      "retrieval_source": "local_dummy",
      "retrieval_ms": 10
    },
    "fallback_reason": null
  }
  ```
- **说明**：
  - `tools_allowed` 为空则不触发工具。
  - `metadata.use_enhanced_retrieval=true` 时会走增强检索（当前为内置 stub）。
  - `rag.threshold` 为 KB 命中阈值，`top_k` 为返回条数。

## 调试示例
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session",
    "message": {
      "sender": "user",
      "receiver": "bot",
      "channel": "web",
      "message_type": "text",
      "content": "查询订单 ORD-202401001"
    },
    "tools_allowed": ["lookup_order"],
    "metadata": {"use_enhanced_retrieval": true}
  }'
```
