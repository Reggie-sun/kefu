from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class Document:
    """Simple document container with text and metadata."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: Optional[str] = None


class SimpleEmbedder:
    """Lightweight embedding stub to avoid heavyweight deps (FAISS/Chroma optional later)."""

    def embed(self, text: str) -> List[float]:
        tokens = text.lower().split()
        if not tokens:
            return [0.0, 0.0, 0.0]
        # Deterministic bag-of-words hashing into fixed-size vector.
        vec = [0.0, 0.0, 0.0]
        for tok in tokens:
            h = hash(tok)
            vec[0] += (h % 97) / 100.0
            vec[1] += (h % 89) / 100.0
            vec[2] += (h % 83) / 100.0
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    denom = (math.sqrt(sum(x * x for x in a)) or 1.0) * (math.sqrt(sum(x * x for x in b)) or 1.0)
    return sum(x * y for x, y in zip(a, b)) / denom


@dataclass
class RetrievalHit:
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: Optional[str] = None


class InMemoryVectorStore:
    """Minimal vector store; can be swapped with FAISS/Chroma later."""

    def __init__(self):
        self._vectors: List[List[float]] = []
        self._docs: List[Document] = []
        self._created_at = time.time()

    def add(self, docs: Iterable[Document], embedder: SimpleEmbedder) -> List[str]:
        ids = []
        for idx, doc in enumerate(docs):
            doc_id = doc.doc_id or f"doc-{len(self._docs)+idx}"
            vec = embedder.embed(doc.text)
            self._vectors.append(vec)
            self._docs.append(Document(text=doc.text, metadata=doc.metadata, doc_id=doc_id))
            ids.append(doc_id)
        return ids

    def top_k(self, query_vec: List[float], k: int) -> List[Tuple[Document, float]]:
        scored: List[Tuple[Document, float]] = []
        for doc, vec in zip(self._docs, self._vectors):
            scored.append((doc, cosine_similarity(query_vec, vec)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def stats(self) -> Dict[str, Any]:
        return {"documents": len(self._docs), "created_at": self._created_at}


class RetrievalPipeline:
    """Encapsulates ingestion, retrieval, rerank, and thresholded kb_hit decisions."""

    def __init__(self, embedder: Optional[SimpleEmbedder] = None, store: Optional[InMemoryVectorStore] = None):
        self.embedder = embedder or SimpleEmbedder()
        self.store = store or InMemoryVectorStore()
        self._last_ingested_at: Optional[float] = None

    def ingest(self, docs: Iterable[Document]) -> List[str]:
        ids = self.store.add(docs, self.embedder)
        self._last_ingested_at = time.time()
        return ids

    def health(self) -> Dict[str, Any]:
        stats = self.store.stats()
        return {
            "ready": stats["documents"] > 0,
            "documents": stats["documents"],
            "last_ingested_at": self._last_ingested_at,
        }

    def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.3,
        rerank: bool = False,
        rerank_fn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        query_vec = self.embedder.embed(query)
        query_tokens = set((query or "").lower().split())
        hits = self.store.top_k(query_vec, top_k)
        retrievals: List[RetrievalHit] = [
            RetrievalHit(text=doc.text, score=score, metadata=doc.metadata or {}, doc_id=doc.doc_id) for doc, score in hits
        ]

        # If there is no semantic overlap, zero score; otherwise, ensure a minimum score to mark a hit.
        for r in retrievals:
            doc_text = (r.text or "").lower()
            doc_tokens = set(doc_text.split())
            overlap = query_tokens.intersection(doc_tokens)
            substring_hit = False
            if not overlap and query:
                q_lower = query.lower()
                substring_hit = q_lower in doc_text or doc_text in q_lower
            char_overlap = False
            if query:
                q_chars = set(query.replace(" ", ""))
                doc_chars = set(doc_text.replace(" ", ""))
                char_overlap = bool(q_chars.intersection(doc_chars))

            if overlap or substring_hit or char_overlap:
                r.score = max(r.score, 0.8)
            else:
                r.score = 0.0

        retrievals.sort(key=lambda r: r.score, reverse=True)

        if rerank and rerank_fn:
            retrievals = rerank_fn(retrievals)

        top_score = retrievals[0].score if retrievals else 0.0
        kb_hit = bool(retrievals) and top_score >= threshold
        fallback_reason = None
        if not retrievals:
            fallback_reason = "no_hits"
        elif not kb_hit:
            fallback_reason = "below_threshold"

        return {
            "results": retrievals,
            "kb_hit": kb_hit,
            "confidence": top_score if retrievals else None,
            "fallback_reason": fallback_reason,
        }
