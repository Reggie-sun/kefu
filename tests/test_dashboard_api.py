import os
import tempfile
import unittest

from fastapi.testclient import TestClient

# Ensure we use an isolated SQLite file for the dashboard store.
tmp_path = os.path.join(tempfile.gettempdir(), "dashboard_test.sqlite3")
os.environ["GATEWAY_LOG_DB"] = f"sqlite:///{tmp_path}"

from gateway.logging_store import LogRecord, LoggingStore
from dashboard.app import app


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        store = LoggingStore(os.environ["GATEWAY_LOG_DB"])
        store.append(
            LogRecord(
                session_id="s1",
                channel="wechat",
                user_message="hello",
                model_response="hi",
                kb_hit=True,
                confidence=0.8,
                tool_calls=[{"name": "lookup_order", "status": "success"}],
                retrieved=[{"text": "refund policy", "score": 0.9}],
                latency={"total_ms": 10},
                trace_id="t1",
            )
        )

    def test_logs_endpoint(self):
        resp = self.client.get("/api/logs?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], "s1")

    def test_stats_endpoint(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        stats = resp.json()
        self.assertGreaterEqual(stats["total_conversations"], 1)
        self.assertIn("kb_hit_rate", stats)
        self.assertIn("tool_usage", stats)
        self.assertIn("daily_volume", stats)

    def test_index_serves_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))


if __name__ == "__main__":
    unittest.main()
