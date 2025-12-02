from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, List, Optional

from gateway.retrieval import Document, RetrievalHit, RetrievalPipeline


@dataclass
class EnhancedRetrievalResult:
    hits: List[RetrievalHit]
    confidence: Optional[float]
    kb_hit: bool
    fallback_reason: Optional[str]
    source: str
    response_time_ms: int


class DummyEnhancedRetrieval:
    """
    Minimal stub for enhanced retrieval.
    Uses the local RetrievalPipeline so the API shape matches the expected interface
    without introducing external dependencies.
    """

    def __init__(self) -> None:
        self.pipeline = RetrievalPipeline()
        # Seed with the same lightweight snippets as the base pipeline.
        self.pipeline.ingest(
            [
                Document(text="退款政策支持七天无理由退货退款", metadata={"tag": "refund"}),
                Document(text="物流状态每天更新，支持快递跟踪", metadata={"tag": "logistics"}),
                Document(text="产品信息包含SKU和库存数据", metadata={"tag": "product"}),
            ]
        )

    async def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.3,
        rerank: bool = False,
        session_id: Optional[str] = None,
        use_rag_first: bool = True,
        **_: Any,
    ) -> EnhancedRetrievalResult:
        start = time.perf_counter()
        result = self.pipeline.search(query=query or "", top_k=top_k, threshold=threshold, rerank=rerank)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        hits: List[RetrievalHit] = result.get("results", [])
        return EnhancedRetrievalResult(
            hits=hits,
            confidence=result.get("confidence"),
            kb_hit=bool(result.get("kb_hit")),
            fallback_reason=result.get("fallback_reason"),
            source="local_dummy",
            response_time_ms=elapsed_ms,
        )


def get_enhanced_retrieval() -> DummyEnhancedRetrieval:
    """
    Factory returning the enhanced retrieval instance.
    In the future this can load remote RAG services; for now it provides a stub.
    """
    return DummyEnhancedRetrieval()
