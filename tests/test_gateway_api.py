import unittest

from fastapi.testclient import TestClient

from gateway.app import app


class GatewayApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_chat_endpoint_returns_structured_reply(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "hello",
            },
            "tools_allowed": [],
            "rag": {"top_k": 3, "threshold": 0.3},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["reply_text"], "hello")
        self.assertIn("latency", data)
        self.assertIn("kb_hit", data)
        self.assertIn("tool_traces", data)
        self.assertIn("source_refs", data)
        self.assertIsInstance(data["retrieved"], list)
        self.assertIsInstance(data["tool_traces"], list)
        self.assertEqual(data.get("tool_calls"), data["tool_traces"])
        self.assertGreaterEqual(data["latency"]["total_ms"], 0)
        self.assertIn("retrieval_ms", data["latency"])
        self.assertIn("tool_ms", data["latency"])

    def test_healthz(self):
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_chat_endpoint_requires_content_or_media(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "image",
                "content": None,
                "media_url": None,
            },
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_rag_hit_sets_kb_hit_and_confidence(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "退款政策是什么",
            },
            "rag": {"top_k": 2, "threshold": 0.05},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["kb_hit"])
        self.assertIsNotNone(data["confidence"])
        self.assertEqual(data["fallback_reason"], None)
        self.assertGreaterEqual(len(data["retrieved"]), 1)

    def test_rag_below_threshold_sets_fallback_reason(self):
        payload = {
            "session_id": "s1",
            "message": {
                "sender": "u1",
                "receiver": "bot",
                "channel": "wechat",
                "message_type": "text",
                "content": "完全不相关的句子",
            },
            "rag": {"top_k": 1, "threshold": 0.99},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["kb_hit"])
        self.assertEqual(data["fallback_reason"], "below_threshold")


if __name__ == "__main__":
    unittest.main()
