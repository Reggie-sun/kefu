import os
import tempfile
import time
from typing import Any, Dict, List, Optional

import httpx
import openai
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gateway.retrieval import Document, RetrievalPipeline
from gateway.enhanced_retrieval import get_enhanced_retrieval
from gateway.enhanced_tools import EnhancedToolsRouter
from gateway.logging_store import LogRecord, LoggingStore
from gateway.tools import route_tools

class UnifiedMessageModel(BaseModel):
    sender: str
    receiver: str
    channel: str
    message_type: str
    content: Any
    timestamp: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_id: Optional[str] = None
    media_url: Optional[str] = None

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, v):
        return v or {}

    @model_validator(mode="after")
    def validate_payload(self) -> "UnifiedMessageModel":
        message_type = self.message_type or ""
        content = self.content
        media_url = self.media_url
        has_articles = isinstance(self.metadata, dict) and bool(self.metadata.get("articles"))
        # Require content or media for common media types; allow news with articles metadata.
        if message_type.startswith("event."):
            return self
        if message_type in {"text", "voice", "image", "video", "file"} and content is None and media_url is None:
            raise ValueError("content or media_url required for message_type={}".format(message_type))
        if message_type == "news" and not (content or has_articles):
            raise ValueError("news message requires content or articles metadata")
        return self


class GatewayRagConfigModel(BaseModel):
    top_k: int = Field(default=3, ge=1, le=20)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class GatewayRequestModel(BaseModel):
    session_id: str
    message: UnifiedMessageModel
    tools_allowed: List[str] = Field(default_factory=list)
    rag: GatewayRagConfigModel = Field(default_factory=GatewayRagConfigModel)
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GatewayResponseModel(BaseModel):
    reply_text: str
    kb_hit: Optional[bool] = None
    confidence: Optional[float] = None
    retrieved: List[Dict[str, Any]] = Field(default_factory=list)
    tool_traces: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)
    latency: Dict[str, Any] = Field(default_factory=dict)
    fallback_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


app = FastAPI(title="Smart Gateway", version="0.2.0")
RETRIEVAL_TIMEOUT_MS = int(os.environ.get("RETRIEVAL_TIMEOUT_MS", "60000"))
TOOL_TIMEOUT_MS = 500
LLM_TIMEOUT_MS = 400
# 相似度阈值（超过才认为命中，可通过环境变量 RAG_CONF_THRESHOLD 覆盖）
RAG_CONF_THRESHOLD = float(os.environ.get("RAG_CONF_THRESHOLD", "0.7"))

# Initialize enhanced retrieval service
_enhanced_retrieval = get_enhanced_retrieval()

# Initialize a lightweight retrieval pipeline with sample KB snippets for tests/demo.
_pipeline = RetrievalPipeline()
_pipeline.ingest(
    [
        Document(text="退款政策支持七天无理由退货退款", metadata={"tag": "refund"}),
        Document(text="物流状态每天更新，支持快递跟踪", metadata={"tag": "logistics"}),
        Document(text="产品信息包含SKU和库存数据", metadata={"tag": "product"}),
    ]
)

# Logging store (SQLite by default)
LOG_DB_URL = os.environ.get("GATEWAY_LOG_DB", f"sqlite:///{os.path.join(tempfile.gettempdir(), 'gateway_logs.sqlite3')}")
_log_store: Optional[LoggingStore] = None
try:
    _log_store = LoggingStore(LOG_DB_URL)
except Exception:
    _log_store = None

# Toggle enhanced tool router via env for gradual adoption.
USE_ENHANCED_TOOLS = os.environ.get("USE_ENHANCED_TOOLS", "").lower() in {"1", "true", "yes"}
_enhanced_tools_router: Optional[EnhancedToolsRouter] = EnhancedToolsRouter() if USE_ENHANCED_TOOLS else None

# Optional external customer-service RAG client
_customer_rag_base = os.environ.get("CUSTOMER_SERVICE_API_BASE_URL", "").rstrip("/")
_customer_rag_token = os.environ.get("CUSTOMER_SERVICE_API_TOKEN", "")
_customer_rag_timeout = float(os.environ.get("CUSTOMER_SERVICE_API_TIMEOUT", "8.0"))
_customer_rag_proxy = os.environ.get("CUSTOMER_SERVICE_API_PROXY", None)
_customer_rag_client: Optional[httpx.AsyncClient] = None
EXTERNAL_RAG_ONLY = os.environ.get("EXTERNAL_RAG_ONLY", "").lower() in {"1", "true", "yes"}
# LLM settings (用于占位 LLM 回答)
_llm_api_key = os.environ.get("open_ai_api_key") or os.environ.get("OPENAI_API_KEY")
_llm_api_base = os.environ.get("open_ai_api_base") or os.environ.get("OPENAI_API_BASE")
_llm_model = os.environ.get("model") or "gpt-3.5-turbo"
if _llm_api_key:
    openai.api_key = _llm_api_key
if _llm_api_base:
    openai.api_base = _llm_api_base
_logger = None
try:
    from common.log import logger as _logger
except Exception:
    import logging as _logger
    _logger = _logger.getLogger(__name__)


def _extract_rag_summary(answer: str) -> str:
    """
    从 RAG 返回的富文本 answer 中，只提取“摘要速览”部分，用于对外回复。
    若找不到“摘要速览”标记，则返回原文。
    """
    if not isinstance(answer, str) or not answer:
        return answer

    marker = "摘要速览"
    idx = answer.find(marker)
    if idx == -1:
        return answer

    segment = answer[idx:]
    # 跳过“摘要速览”这一行标题
    nl = segment.find("\n")
    body = segment[nl + 1 :] if nl != -1 else segment[len(marker) :]

    # 截断到下一个章节标题（#### 或 ###）
    cut_pos = len(body)
    for h in ("\n#### ", "\n### "):
        pos = body.find(h)
        if pos != -1 and pos < cut_pos:
            cut_pos = pos
    body = body[:cut_pos].strip()
    if not body:
        return answer
    return f"摘要速览\n{body}"


async def _call_customer_service_rag(
    question: str,
    session_id: str,
    top_k: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Call external customer service RAG if configured.
    Returns dict with keys: answer, citations, latency_ms, retrieved (normalized list).
    """
    if not _customer_rag_base:
        return None
    global _customer_rag_client
    if _customer_rag_client is None:
        _customer_rag_client = httpx.AsyncClient(
            timeout=_customer_rag_timeout,
            trust_env=False,  # avoid picking up system proxy unless explicitly set
        )
    url = f"{_customer_rag_base}/integrations/customer-service/ask"
    headers = {}
    if _customer_rag_token:
        headers["X-Customer-Service-Token"] = _customer_rag_token

    payload = {
        "question": question,
        "session_id": session_id,
        "top_k": top_k,
        "allow_web": False,
        "doc_only": True,
        "metadata": metadata or {},
    }
    start = time.perf_counter()
    _logger.info("[gateway] calling customer_service_rag url=%s top_k=%s", url, top_k)
    resp = await _customer_rag_client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    citations = data.get("citations") or []
    retrieved = []
    for c in citations:
        text = c.get("text") or c.get("chunk") or c.get("content")
        score = c.get("score")
        retrieved.append(
            {
                "text": text,
                "score": score if score is not None else 0.0,
                "metadata": c.get("metadata") or {},
                "source": c.get("source") or c.get("doc_id"),
                "doc_id": c.get("doc_id"),
            }
        )
    return {
        "answer": data.get("answer"),
        "citations": citations,
        "retrieved": retrieved,
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/routes")
async def list_routes():
    """Return registered HTTP routes for quick inspection/testing."""
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "methods": sorted(route.methods or []),
                    "name": route.name,
                    "summary": route.summary or "",
                    "response_model": getattr(route, "response_model", None).__name__
                    if getattr(route, "response_model", None)
                    else None,
                }
            )
    routes.sort(key=lambda r: r["path"])
    return {"routes": routes, "count": len(routes)}


@app.post("/chat", response_model=GatewayResponseModel)
async def chat(payload: GatewayRequestModel):
    """
    Minimal placeholder implementation for /chat.
    Accepts UnifiedMessage and returns structured response with latency breakdown, tool traces, and retrieval placeholders.
    """
    start = time.perf_counter()
    try:
        content = payload.message.content
        reply_text = content if isinstance(content, str) else str(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid message payload: {exc}")

    latency: Dict[str, Any] = {}
    tool_traces: List[Dict[str, Any]] = []
    retrieved: List[Dict[str, Any]] = []
    source_refs: List[Dict[str, Any]] = []
    fallback_reason: Optional[str] = "stub"
    kb_hit = False
    confidence: Optional[float] = None

    # Retrieval stage
    r_start = time.perf_counter()

    # Use enhanced retrieval if available
    use_enhanced = payload.metadata.get("use_enhanced_retrieval", True)

    if use_enhanced:
        try:
            external_used = False
            # Try external customer-service RAG first if configured.
            if _customer_rag_base:
                try:
                    ext_res = await _call_customer_service_rag(
                        reply_text,
                        session_id=payload.session_id,
                        top_k=payload.rag.top_k,
                        metadata=payload.metadata,
                    )
                    if ext_res is not None:
                        external_used = True
                        retrieved = ext_res["retrieved"]
                        source_refs = retrieved
                        latency["retrieval_source"] = "customer_service"
                        latency["retrieval_ms"] = ext_res.get("latency_ms", 0)
                        confidence = retrieved[0]["score"] if retrieved else None
                        kb_hit = bool(retrieved)
                        # Prefer external answer if present
                        if ext_res.get("answer"):
                            reply_text = _extract_rag_summary(ext_res["answer"])
                        fallback_reason = None if kb_hit else "no_hits"
                except Exception as exc:
                    # External call failed; fall back to enhanced/local.
                    external_used = False
                    _logger.warning("[gateway] customer_service_rag failed: %s", exc)

            # If external RAG was configured and used, do not fall back to local dummy when EXTERNAL_RAG_ONLY is set.
            if external_used:
                if not kb_hit:
                    fallback_reason = fallback_reason or "no_hits"
                latency["retrieval_source"] = latency.get("retrieval_source") or "customer_service"
                latency["retrieval_ms"] = latency.get("retrieval_ms") or int((time.perf_counter() - r_start) * 1000)
                # If external only mode is off, allow local fallback; otherwise keep kb_hit False.
                if EXTERNAL_RAG_ONLY and not kb_hit:
                    pass
                elif not EXTERNAL_RAG_ONLY and not kb_hit:
                    external_used = False  # allow local path below

            if not external_used:
                # Use enhanced retrieval service (local dummy) as before.
                enhanced_result = await _enhanced_retrieval.search(
                    query=reply_text,
                    top_k=payload.rag.top_k,
                    threshold=payload.rag.threshold,
                    rerank=payload.metadata.get("rerank", False),
                    session_id=payload.session_id,
                    use_rag_first=payload.metadata.get("use_rag_first", True),
                )

                confidence = enhanced_result.confidence
                kb_hit = enhanced_result.kb_hit
                fallback_reason = enhanced_result.fallback_reason
                retrieved = [
                    {"text": h.text, "score": h.score, "metadata": h.metadata, "doc_id": h.doc_id}
                    for h in enhanced_result.hits
                ]
                source_refs = retrieved
                # 若检索命中且未有外部答案，使用首条命中内容作为回复
                if kb_hit and retrieved and not ext_res:
                    reply_text = retrieved[0]["text"]
                # Add retrieval metadata
                latency["retrieval_source"] = latency.get("retrieval_source") or enhanced_result.source
                latency["retrieval_ms"] = enhanced_result.response_time_ms

        except Exception as e:
            _logger.exception("[gateway] retrieval error: %s", e)
            # Only fall back to local when EXTERNAL_RAG_ONLY is False
            retrieval_ready = _pipeline.health()["ready"]
            if not EXTERNAL_RAG_ONLY and retrieval_ready:
                if payload.metadata.get("simulate_retrieval_delay_ms"):
                    time.sleep(payload.metadata["simulate_retrieval_delay_ms"] / 1000.0)
                r = _pipeline.search(
                    query=reply_text,
                    top_k=payload.rag.top_k,
                    threshold=payload.rag.threshold,
                    rerank=payload.metadata.get("rerank", False),
                )
                confidence = r["confidence"]
                kb_hit = r["kb_hit"]
                fallback_reason = r["fallback_reason"]
                retrieved = [{"text": h.text, "score": h.score, "metadata": h.metadata, "doc_id": h.doc_id} for h in r["results"]]
                source_refs = retrieved
                latency["retrieval_source"] = "local"
                latency["retrieval_ms"] = int((time.perf_counter() - r_start) * 1000)
            else:
                fallback_reason = "rag_unready"
                latency["retrieval_source"] = "customer_service_error"
                latency["retrieval_ms"] = int((time.perf_counter() - r_start) * 1000)
        # Final safety: if still no kb_hit, try local fallback once (only when external not used).
        if not kb_hit and not (latency.get("retrieval_source") == "customer_service"):
            local_r = _pipeline.search(
                query=reply_text,
                top_k=payload.rag.top_k,
                threshold=payload.rag.threshold,
                rerank=payload.metadata.get("rerank", False),
            )
            if local_r["kb_hit"]:
                kb_hit = True
                confidence = local_r["confidence"]
                fallback_reason = None
                retrieved = [
                    {"text": h.text, "score": h.score, "metadata": h.metadata, "doc_id": h.doc_id}
                    for h in local_r["results"]
                ]
                source_refs = retrieved
                latency["retrieval_source"] = "local_fallback"
                latency["retrieval_ms"] = latency.get("retrieval_ms") or int((time.perf_counter() - r_start) * 1000)
            else:
                fallback_reason = fallback_reason or local_r["fallback_reason"]
    else:
        # Use local retrieval
        retrieval_ready = _pipeline.health()["ready"]
        if payload.metadata.get("simulate_retrieval_delay_ms"):
            time.sleep(payload.metadata["simulate_retrieval_delay_ms"] / 1000.0)
        if retrieval_ready:
            r = _pipeline.search(
                query=reply_text,
                top_k=payload.rag.top_k,
                threshold=payload.rag.threshold,
                rerank=payload.metadata.get("rerank", False),
            )
            confidence = r["confidence"]
            kb_hit = r["kb_hit"]
            fallback_reason = r["fallback_reason"]
            retrieved = [{"text": h.text, "score": h.score, "metadata": h.metadata, "doc_id": h.doc_id} for h in r["results"]]
            source_refs = retrieved
        else:
            fallback_reason = "rag_unready"
        latency["retrieval_source"] = "local"
        latency["retrieval_ms"] = int((time.perf_counter() - r_start) * 1000)

    if latency["retrieval_ms"] > RETRIEVAL_TIMEOUT_MS:
        fallback_reason = "retrieval_timeout"
        kb_hit = False

    # 如果相似度较低，提醒用户并标记为低置信度
    if confidence is not None and confidence < RAG_CONF_THRESHOLD:
        latency["low_confidence"] = True
        fallback_reason = fallback_reason or "low_confidence"
        kb_hit = False  # 低置信度视为未命中，走本地/LLM 回答逻辑
        note = "当前检索未找到相似度≥{:.0%}的内容，将用本地大语言模型回答。".format(RAG_CONF_THRESHOLD)
        if isinstance(reply_text, str) and reply_text:
            reply_text = f"{note}\n{reply_text}"
        else:
            reply_text = note

    # LLM 生成阶段：使用检索片段作为上下文，尽量给出正式答案
    llm_ms: Optional[int] = None
    # 如果已经使用了外部 RAG（customer_service），优先信任其 answer，
    # 不再用本地 LLM 覆盖，避免丢失 RAG 端完整回答。
    use_local_llm = _llm_api_key and latency.get("retrieval_source") != "customer_service"
    if use_local_llm:
        try:
            llm_start = time.perf_counter()
            context_snippets = "\n\n".join(
                [f"[score={r.get('score', 0):.2f}] {r.get('text','')}" for r in retrieved][:3]
            )
            user_question = payload.message.content if isinstance(payload.message.content, str) else str(payload.message.content)
            prompt = (
                "请基于以下检索片段回答用户问题；若片段为空再自行回答。\n"
                f"用户问题：{user_question}\n"
                f"检索片段：\n{context_snippets}\n"
                "请用简洁中文回答。"
            )
            resp = openai.ChatCompletion.create(
                model=_llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            reply_text = resp["choices"][0]["message"]["content"].strip()
            llm_ms = int((time.perf_counter() - llm_start) * 1000)
            fallback_reason = None
        except Exception as e:  # pragma: no cover
            _logger.warning("[gateway] LLM fallback failed: %s", e)

    # Tool routing (rule_based or react) if enabled
    t_start = time.perf_counter()
    routing_mode = payload.metadata.get("routing_mode") or "rule_based"
    use_enhanced_tools = payload.metadata.get("use_enhanced_tools", USE_ENHANCED_TOOLS)
    if payload.tools_allowed and isinstance(payload.message.content, str):
        tool_results: List[Any] = []
        try:
            if use_enhanced_tools:
                router = _enhanced_tools_router or EnhancedToolsRouter()
                tool_results = await router.route_and_execute(
                    payload.message.content,
                    payload.tools_allowed,
                    routing_mode=routing_mode,
                    user_id=payload.message.sender,
                )
            else:
                tool_results = route_tools(payload.message.content, payload.tools_allowed, routing_mode=routing_mode)
        except Exception:
            tool_results = []
            fallback_reason = "tool_error"

        tool_traces = [t.to_dict() for t in tool_results]
        if tool_results:
            success = tool_results[0].status == "success"
            if success:
                reply_text = reply_text or ""
                reply_text = f"{reply_text}\n[tool:{tool_results[0].name}]" if reply_text else f"[tool:{tool_results[0].name}]"
                fallback_reason = fallback_reason if kb_hit else None
            else:
                fallback_reason = "tool_error"
    latency["tool_ms"] = int((time.perf_counter() - t_start) * 1000)
    if latency["tool_ms"] > TOOL_TIMEOUT_MS:
        fallback_reason = "tool_timeout"

    # LLM / answer compose stage (stub)
    llm_start = time.perf_counter()
    if not kb_hit:
        # simple stub fallback answer
        reply_text = reply_text or "抱歉，暂时无法找到相关信息"
    latency["llm_ms"] = int((time.perf_counter() - llm_start) * 1000)
    if latency["llm_ms"] > LLM_TIMEOUT_MS:
        fallback_reason = fallback_reason or "llm_timeout"

    # 如果检索命中但未形成回复，兜底用首条检索文本或固定文案
    if kb_hit and (not reply_text or not str(reply_text).strip()):
        if retrieved:
            reply_text = retrieved[0].get("text") or ""
        reply_text = reply_text or "抱歉，暂时无法找到相关信息"
        fallback_reason = fallback_reason or "rag_answer_empty"

    # 相似度提示与低置信度兜底
    # 若未得到confidence但有检索结果，则取首条得分；否则默认0.0
    if confidence is None:
        if retrieved and isinstance(retrieved[0].get("score"), (int, float)):
            confidence = float(retrieved[0]["score"])
        else:
            confidence = 0.0
    if confidence < RAG_CONF_THRESHOLD:
        latency["low_confidence"] = True
        fallback_reason = fallback_reason or "low_confidence"
        kb_hit = False  # 低置信度视为未命中，触发本地/LLM提示
        # 清空低置信度检索结果，避免误导
        retrieved = []
        source_refs = []
        note = "当前检索未找到相似度≥{:.0%}的内容，将用本地大语言模型回答。".format(RAG_CONF_THRESHOLD)
        if llm_ms is not None and reply_text:
            # 保留 LLM 的回答，同时加上提示
            reply_text = f"{note}\n{reply_text}"
        else:
            reply_text = note

    # 在回复前统一加上相似度提示与外部 RAG 标记
    if latency.get("retrieval_source") == "customer_service":
        rag_note = "【已调用外部 RAG 服务（可能稍慢）】"
        reply_text = f"{rag_note}\n{reply_text}" if reply_text else rag_note
    sim_line = f"相似度: {confidence:.2f}"
    reply_text = f"{sim_line}\n{reply_text}" if reply_text else sim_line

    total_ms = int((time.perf_counter() - start) * 1000)
    latency["total_ms"] = total_ms
    if llm_ms is not None:
        latency["llm_ms"] = llm_ms

    response = GatewayResponseModel(
        reply_text=reply_text,
        kb_hit=kb_hit,
        confidence=confidence,
        retrieved=retrieved,
        tool_traces=tool_traces,
        tool_calls=tool_traces,  # keep backward compatibility
        source_refs=source_refs,
        latency=latency,
        fallback_reason=fallback_reason,
    )
    # Persist log asynchronously if available; ignore errors to avoid user impact.
    if _log_store:
        try:
            _log_store.append(
                LogRecord(
                    session_id=payload.session_id,
                    channel=payload.message.channel,
                    user_message=str(payload.message.content),
                    model_response=response.reply_text,
                    kb_hit=kb_hit,
                    confidence=confidence,
                    tool_calls=tool_traces,
                    retrieved=retrieved,
                    latency=latency,
                    trace_id=payload.trace_id,
                )
            )
        except Exception:
            pass
    return response
