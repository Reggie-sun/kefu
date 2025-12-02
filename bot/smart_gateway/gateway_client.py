import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import requests

from common.log import logger
from common.unified_message import UnifiedMessage


@dataclass
class GatewayRagConfig:
    top_k: int = 3
    threshold: float = 0.3


@dataclass
class GatewayRequest:
    session_id: str
    message: UnifiedMessage
    tools_allowed: List[str] = field(default_factory=list)
    rag: GatewayRagConfig = field(default_factory=GatewayRagConfig)
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "session_id": self.session_id,
            "message": asdict(self.message),
            "tools_allowed": self.tools_allowed,
            "rag": asdict(self.rag),
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }
        # Remove None fields to keep payload clean.
        return {k: v for k, v in payload.items() if v is not None}


@dataclass
class GatewayResponse:
    reply_text: str
    kb_hit: Optional[bool] = None
    confidence: Optional[float] = None
    retrieved: Optional[List[Dict[str, Any]]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    latency: Optional[Dict[str, Any]] = None
    fallback_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatewayResponse":
        return cls(
            reply_text=data.get("reply_text") or data.get("content") or "",
            kb_hit=data.get("kb_hit"),
            confidence=data.get("confidence"),
            retrieved=data.get("retrieved") or data.get("retrieved_chunks"),
            tool_calls=data.get("tool_calls"),
            latency=data.get("latency"),
            fallback_reason=data.get("fallback_reason"),
        )


class GatewayClient:
    def __init__(
        self,
        base_url: str,
        timeout: int = 15,
        default_tools: Optional[List[str]] = None,
        default_rag: Optional[GatewayRagConfig] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_tools = default_tools or []
        self.default_rag = default_rag or GatewayRagConfig()

    def chat(
        self,
        request: GatewayRequest,
    ) -> GatewayResponse:
        url = f"{self.base_url}/chat"
        payload = request.to_dict()
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return GatewayResponse.from_dict(data)
        except requests.exceptions.RequestException as e:
            body = None
            try:
                body = e.response.text if getattr(e, "response", None) else None
            except Exception:
                body = None
            logger.error("[gateway] request failed: %s payload=%s response=%s", e, payload, body)
            raise
        except json.JSONDecodeError:
            logger.error(f"[gateway] invalid JSON response from {url}")
            raise
