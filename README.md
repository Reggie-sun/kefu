# ChatGPT-on-WeChat 智能客服机器人（带 RAG 检索）

一个基于大模型的微信客服 / 助手系统，集成了：

- 微信公众号聊天机器人（支持纯文本、语音转文字等）
- Smart Gateway：统一接入层（工具调用 + 日志 + RAG）
- 外部文档检索 RAG 服务（支持你自己的知识库）
- Web Dashboard：查看会话日志与检索情况
- 一键 Docker 部署 + 本地调试脚本

本仓库是在开源项目 [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat) 基础上的增强版本，重点强化了 **客服场景 + RAG 集成体验**。

---

## 功能特点

- **微信公众号对接**
  - 支持 `wechatmp` 被动回复模式
  - 支持文字消息、基础指令（如 `#清除记忆`）等

- **Smart Gateway 智能网关**
  - 统一 `/chat` 接口，负责：
    - 调用外部 RAG 服务（文档检索 / 知识库问答）
    - LLM 兜底生成答案
    - 工具调用（如订单查询、物流查询等）
  - 返回结构化字段：`reply_text / kb_hit / confidence / retrieved / latency / fallback_reason`

- **外部 RAG 集成**
  - 通过环境变量配置 `CUSTOMER_SERVICE_API_BASE_URL` 与 `CUSTOMER_SERVICE_API_TOKEN`
  - 网关调用：`POST <base>/integrations/customer-service/ask`
  - 若外部 RAG 成功返回，将优先使用其答案，并在前缀标记：
    - `【已调用外部 RAG 服务（可能稍慢）】`
    - `相似度: X.XX`

- **被动回复 + 长耗时优化**
  - 首次用户提问时，如果检索 / RAG 仍在执行：
    - 立即返回提示：  
      `【已开始调用外部知识库检索，处理可能需要几十秒。稍后回复任意文字以获取本次问题的完整答案】`
  - 等 RAG 处理完成后，用户再次回复任意文本：
    - 返回：  
      `【上一次问题的外部检索已完成，这是计算好的答案】`  
      + 实际答案内容（仅保留 RAG 的“摘要速览”部分）

---

## 目录结构概览

以 `chatgpt-on-wechat` 子目录为根：

- `app.py`：主入口，加载配置 & 启动指定 Channel
- `config-template.json`：默认配置模板（建议复制成 `config.json` 并修改）
- `config.json`：运行时配置
- `config.py`：配置加载与环境变量覆盖逻辑
- `channel/wechatmp/`：微信公众号被动 / 主动回复实现
  - `wechatmp_channel.py`
  - `passive_reply.py` / `active_reply.py`
- `bot/`：各类 Bot 实现
  - `smart_gateway/`：Smart Gateway Bot 封装
  - `openai/`：兼容 OpenAI 接口的 Bot
- `gateway/`：Smart Gateway 服务
  - `app.py`：FastAPI 应用 `/chat` 路由
  - `enhanced_retrieval.py`：本地 Dummy 检索
  - `tools.py` / `enhanced_tools.py`：工具路由
- `dashboard/`：日志 & 检索控制面板（FastAPI + 前端静态文件）
- `start_stack.sh`：本地一键启动 Gateway + Dashboard + WeChatMP Bot
- `docker-compose.deploy.yml`：生产环境 Docker 部署编排
- `start_with_rag.sh`：与本地 RAG 项目联动的启动脚本（可选）

---

## 配置与环境变量

### 1. 基本配置（`config.json`）

从模板复制：

```bash
cp config-template.json config.json
