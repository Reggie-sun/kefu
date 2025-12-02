import asyncio
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from gateway import app


class FakeCustomerRagClient:
    def __init__(self, answer: str, retrieved):
        self.answer = answer
        self.retrieved = retrieved
        self.called = 0

    async def post(self, *args, **kwargs):
        class Resp:
            def __init__(self, answer, retrieved):
                self._answer = answer
                self._retrieved = retrieved

            def raise_for_status(self):
                return None

            def json(self):
                return {"answer": self._answer, "citations": self._retrieved}

        self.called += 1
        return Resp(self.answer, self.retrieved)


class CustomerServiceRagTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)
        self._orig_base = app._customer_rag_base
        self._orig_token = app._customer_rag_token
        self._orig_client = app._customer_rag_client

    def tearDown(self):
        app._customer_rag_client = self._orig_client
        app._customer_rag_base = self._orig_base
        app._customer_rag_token = self._orig_token

    def test_external_rag_used_when_configured(self):
        # Configure external base to trigger usage
        app._customer_rag_base = "http://customer-rag.test"

        fake = FakeCustomerRagClient(
            answer="ext-answer",
            retrieved=[{"text": "cite", "score": 0.9, "metadata": {"src": "kb1"}, "doc_id": "d1"}],
        )
        app._customer_rag_client = fake

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
            "metadata": {},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["reply_text"], "ext-answer")
        self.assertTrue(data["kb_hit"])
        self.assertEqual(data["retrieved"][0]["text"], "cite")
        self.assertEqual(app._customer_rag_client, fake)

    def test_external_rag_failure_falls_back(self):
        app._customer_rag_base = "http://customer-rag.test"

        class FailingClient:
            async def post(self, *args, **kwargs):
                raise RuntimeError("boom")

        app._customer_rag_client = FailingClient()

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
            "metadata": {},
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # fallback path should still return content and not crash
        self.assertIn("reply_text", data)
        self.assertIn("kb_hit", data)


if __name__ == "__main__":
    unittest.main()
