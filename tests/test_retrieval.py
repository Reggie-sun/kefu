import unittest

from gateway.retrieval import Document, RetrievalPipeline


class RetrievalPipelineTests(unittest.TestCase):
    def test_ingest_and_search_returns_kb_hit(self):
        pipeline = RetrievalPipeline()
        docs = [
            Document(text="Refund policy allows returns within seven days", metadata={"tag": "refund"}),
            Document(text="Logistics tracking is updated daily", metadata={"tag": "logistics"}),
        ]
        pipeline.ingest(docs)

        result = pipeline.search(query="refund policy", top_k=2, threshold=0.1)
        self.assertTrue(result["kb_hit"])
        self.assertIsNotNone(result["confidence"])
        self.assertGreaterEqual(result["results"][0].score, result["results"][-1].score)
        self.assertEqual(len(result["results"]), 2)

    def test_threshold_triggers_fallback_but_returns_hits(self):
        pipeline = RetrievalPipeline()
        pipeline.ingest([Document(text="banana bread recipe")])
        result = pipeline.search(query="banana", top_k=1, threshold=1.1)
        self.assertFalse(result["kb_hit"])
        self.assertEqual(result["fallback_reason"], "below_threshold")
        self.assertEqual(len(result["results"]), 1)
        self.assertIsNotNone(result["confidence"])

    def test_rerank_changes_order_when_enabled(self):
        pipeline = RetrievalPipeline()
        docs = [
            Document(text="apples are tasty", metadata={"priority": 1}, doc_id="doc-low"),
            Document(text="tracking logistics", metadata={"priority": 5}, doc_id="doc-high"),
        ]
        pipeline.ingest(docs)

        def rerank_fn(results):
            return list(reversed(results))

        # Query favors apples (doc-low) in base similarity order.
        base = pipeline.search(query="apples", top_k=2, threshold=0.0, rerank=False)
        reranked = pipeline.search(query="apples", top_k=2, threshold=0.0, rerank=True, rerank_fn=rerank_fn)

        base_top = base["results"][0].doc_id
        rerank_top = reranked["results"][0].doc_id
        self.assertNotEqual(base_top, rerank_top)  # rerank should flip order

    def test_health_ready_flag(self):
        pipeline = RetrievalPipeline()
        h0 = pipeline.health()
        self.assertFalse(h0["ready"])
        pipeline.ingest([Document(text="hello world")])
        h1 = pipeline.health()
        self.assertTrue(h1["ready"])
        self.assertGreaterEqual(h1["documents"], 1)


if __name__ == "__main__":
    unittest.main()
