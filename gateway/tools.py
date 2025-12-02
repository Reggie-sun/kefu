from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolCallResult:
    name: str
    status: str
    payload: Dict[str, Any]
    latency_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _mock_tool_payload(name: str, query: str) -> Dict[str, Any]:
    if name == "lookup_order":
        return {"order_id": "ORD-123", "status": "shipped", "query": query}
    if name == "check_logistics":
        return {"tracking_no": "YT123456789", "progress": "in_transit", "query": query}
    if name == "product_info":
        return {"sku": "SKU-001", "stock": 42, "query": query}
    return {"echo": query}


def run_tool(name: str, query: str, timeout_ms: int = 500) -> ToolCallResult:
    start = time.perf_counter()
    q_lower = (query or "").lower()
    # Simulated failures for testing paths
    if "timeout" in q_lower or "超时" in q_lower:
        time.sleep(min(timeout_ms / 1000.0, 0.6))
        raise TimeoutError(f"{name} timed out")
    if "fail" in q_lower or "error" in q_lower or "失败" in query:
        raise RuntimeError(f"{name} failed")

    payload = _mock_tool_payload(name, query)
    latency = int((time.perf_counter() - start) * 1000)
    return ToolCallResult(name=name, status="success", payload=payload, latency_ms=latency)


def rule_based_intent(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(k in t for k in ["订单", "order"]):
        return "lookup_order"
    if any(k in t for k in ["物流", "快递", "logistics", "tracking"]):
        return "check_logistics"
    if any(k in t for k in ["商品", "产品", "product", "sku"]):
        return "product_info"
    return None


def route_tools(user_input: str, tools_allowed: List[str], routing_mode: str = "rule_based") -> List[ToolCallResult]:
    if not tools_allowed:
        return []
    selected: Optional[str] = None
    if routing_mode == "rule_based":
        selected = rule_based_intent(user_input)
    elif routing_mode == "react":
        # For now, reuse rule-based with a different mode tag to keep contract stable.
        selected = rule_based_intent(user_input)
    if selected is None or selected not in tools_allowed:
        return []
    try:
        result = run_tool(selected, user_input)
        result.payload["routing_mode"] = routing_mode
        return [result]
    except Exception as exc:
        latency = 0
        if isinstance(exc, TimeoutError):
            latency = 500
        return [
            ToolCallResult(
                name=selected,
                status="failed",
                payload={"routing_mode": routing_mode},
                latency_ms=latency,
                error=str(exc),
            )
        ]
