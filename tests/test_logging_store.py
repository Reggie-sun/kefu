import os
import tempfile
import unittest

from gateway.logging_store import LogRecord, LoggingStore


class LoggingStoreTests(unittest.TestCase):
    def test_append_and_fetch_recent_sqlite(self):
        path = os.path.join(tempfile.gettempdir(), "test_gateway_logs.sqlite3")
        if os.path.exists(path):
            os.remove(path)
        store = LoggingStore(f"sqlite:///{path}")
        record = LogRecord(
            session_id="s1",
            channel="wechat",
            user_message="hi",
            model_response="hello",
            kb_hit=True,
            confidence=0.9,
            tool_calls=[{"name": "lookup_order", "status": "success"}],
            retrieved=[{"text": "policy", "score": 0.8}],
            latency={"total_ms": 10},
            trace_id="t1",
        )
        store.append(record)
        rows = store.fetch_recent()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["kb_hit"])
        self.assertEqual(row["session_id"], "s1")
        self.assertEqual(row["channel"], "wechat")
        self.assertEqual(row["user_message"], "hi")
        self.assertEqual(row["model_response"], "hello")
        self.assertAlmostEqual(row["confidence"], 0.9)
        self.assertEqual(row["tool_calls"][0]["name"], "lookup_order")
        self.assertIn("total_ms", row["latency"])
        self.assertEqual(row["trace_id"], "t1")


if __name__ == "__main__":
    unittest.main()
