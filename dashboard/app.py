import os
import tempfile
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from gateway.logging_store import LoggingStore

LOG_DB_URL = os.environ.get("GATEWAY_LOG_DB", f"sqlite:///{os.path.join(tempfile.gettempdir(), 'gateway_logs.sqlite3')}")
DEFAULT_GATEWAY_CFG = {
    "base_url": os.environ.get("smart_gateway_base_url") or os.environ.get("SMART_GATEWAY_BASE_URL") or "http://127.0.0.1:8500",
    "timeout": float(os.environ.get("smart_gateway_timeout") or os.environ.get("SMART_GATEWAY_TIMEOUT") or 15),
    "top_k": int(os.environ.get("smart_gateway_rag_top_k") or os.environ.get("SMART_GATEWAY_RAG_TOP_K") or 3),
    "threshold": float(os.environ.get("smart_gateway_rag_threshold") or os.environ.get("SMART_GATEWAY_RAG_THRESHOLD") or 0.3),
    "external_only": (os.environ.get("EXTERNAL_RAG_ONLY") or "").lower() in {"1", "true", "yes"},
}

app = FastAPI(title="Support Dashboard", version="0.1.0")
_store = LoggingStore(LOG_DB_URL)


@app.get("/api/logs")
def get_logs(limit: int = 50) -> List[Dict[str, Any]]:
    limit = min(max(limit, 1), 200)
    return _store.fetch_recent(limit=limit)


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    rows = _store.fetch_recent(limit=500)  # basic window for dashboard
    total = len(rows)
    kb_hits = sum(1 for r in rows if r.get("kb_hit"))
    kb_hit_rate = kb_hits / total if total else 0.0

    tool_counter: Counter[str] = Counter()
    for r in rows:
        for t in r.get("tool_calls") or []:
            name = t.get("name") or "unknown"
            tool_counter[name] += 1

    daily_counter: Dict[str, int] = defaultdict(int)
    for r in rows:
        ts = r.get("created_at") or time.time()
        day = time.strftime("%Y-%m-%d", time.localtime(ts))
        daily_counter[day] += 1

    return {
        "total_conversations": total,
        "kb_hit_rate": kb_hit_rate,
        "tool_usage": tool_counter,
        "daily_volume": daily_counter,
    }


@app.get("/api/gateway-config")
def get_gateway_config() -> Dict[str, Any]:
    """Expose current gateway defaults (from env) for UI reference."""
    return DEFAULT_GATEWAY_CFG


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
