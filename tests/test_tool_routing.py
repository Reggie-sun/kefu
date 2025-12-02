import unittest

from fastapi.testclient import TestClient

from gateway.app import app
from gateway.tools import route_tools


class ToolRoutingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_rule_based_lookup_order_success(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "帮我查一下订单123",
            },
            "tools_allowed": ["lookup_order", "check_logistics", "product_info"],
            "metadata": {"routing_mode": "rule_based"},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["tool_traces"]), 1)
        self.assertEqual(data["tool_traces"][0]["name"], "lookup_order")
        self.assertEqual(data["tool_traces"][0]["status"], "success")
        self.assertIsNone(data["fallback_reason"])
        self.assertGreaterEqual(data["latency"]["tool_ms"], 0)

    def test_tool_failure_sets_fallback_reason(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "订单查询失败案例",
            },
            "tools_allowed": ["lookup_order"],
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["tool_traces"]), 1)
        self.assertEqual(data["tool_traces"][0]["status"], "failed")
        self.assertEqual(data["fallback_reason"], "tool_error")

    def test_react_mode_still_routes(self):
        traces = route_tools("查物流状态", ["check_logistics"], routing_mode="react")
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].name, "check_logistics")
        self.assertEqual(traces[0].payload["routing_mode"], "react")

    def test_enhanced_tools_router_lookup_order(self):
        payload = {
            "session_id": "s2",
            "message": {
                "sender": "u2",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "查询订单 ORD-202401001",
            },
            "tools_allowed": ["lookup_order"],
            "metadata": {"routing_mode": "rule_based", "use_enhanced_tools": True},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data["tool_traces"]), 1)
        self.assertEqual(data["tool_traces"][0]["name"], "lookup_order")
        self.assertEqual(data["tool_traces"][0]["status"], "success")
        self.assertIsNone(data["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
