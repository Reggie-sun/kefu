from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg2  # type: ignore
except ImportError:  # pragma: no cover
    psycopg2 = None


@dataclass
class LogRecord:
    session_id: str
    channel: str
    user_message: str
    model_response: str
    kb_hit: Optional[bool] = None
    confidence: Optional[float] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    retrieved: Optional[List[Dict[str, Any]]] = None
    latency: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    created_at: Optional[float] = None


class LoggingStore:
    """Persist chat logs to SQLite (default) or Postgres (optional)."""

    def __init__(self, url: str):
        self.url = url
        if url.startswith("sqlite:///"):
            self.backend = "sqlite"
            self.path = url.replace("sqlite:///", "", 1)
            if self.path != ":memory:":
                os.makedirs(os.path.dirname(self.path), exist_ok=True) if os.path.dirname(self.path) else None
        elif url.startswith("postgres://") or url.startswith("postgresql://"):
            self.backend = "postgres"
            if psycopg2 is None:
                raise ImportError("psycopg2 is required for Postgres logging")
        else:
            raise ValueError(f"Unsupported logging url: {url}")
        self.ensure_table()

    def _connect(self):
        if self.backend == "sqlite":
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            return conn
        conn = psycopg2.connect(self.url)  # pragma: no cover
        return conn

    def ensure_table(self):
        ddl = """
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            channel TEXT,
            user_message TEXT,
            model_response TEXT,
            kb_hit INTEGER,
            confidence REAL,
            tool_calls TEXT,
            retrieved TEXT,
            latency TEXT,
            trace_id TEXT,
            created_at REAL
        );
        """
        with self._connect() as conn:
            conn.execute(ddl)
            conn.commit()

    def append(self, record: LogRecord) -> None:
        created_at = record.created_at or time.time()
        tool_calls_json = json.dumps(record.tool_calls or [])
        retrieved_json = json.dumps(record.retrieved or [])
        latency_json = json.dumps(record.latency or {})
        kb_hit_val = None
        if record.kb_hit is not None:
            kb_hit_val = 1 if record.kb_hit else 0

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_logs (
                    session_id, channel, user_message, model_response, kb_hit, confidence,
                    tool_calls, retrieved, latency, trace_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.session_id,
                    record.channel,
                    record.user_message,
                    record.model_response,
                    kb_hit_val,
                    record.confidence,
                    tool_calls_json,
                    retrieved_json,
                    latency_json,
                    record.trace_id,
                    created_at,
                ),
            )
            conn.commit()

    def fetch_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM chat_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            as_dict = dict(row)
            as_dict["kb_hit"] = None if as_dict["kb_hit"] is None else bool(as_dict["kb_hit"])
            as_dict["tool_calls"] = json.loads(as_dict["tool_calls"] or "[]")
            as_dict["retrieved"] = json.loads(as_dict["retrieved"] or "[]")
            as_dict["latency"] = json.loads(as_dict["latency"] or "{}")
            results.append(as_dict)
        return results
