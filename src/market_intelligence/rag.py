"""Dependency-free local RAG index for filings and earnings transcripts.

The index is intentionally small and deterministic for a single service
instance.  A production deployment can implement the same two methods on a
pgvector/Qdrant-backed class without changing the graph.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


def _terms(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-zA-Z]{3,}", text.lower()))


@dataclass(frozen=True)
class DocumentChunk:
    ticker: str
    source: str
    text: str
    chunk_id: str


class LocalRagIndex:
    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []

    def ingest(self, ticker: str, source: str, text: str, chunk_size: int = 900) -> int:
        words = text.split()
        chunks = [" ".join(words[start : start + chunk_size]) for start in range(0, len(words), chunk_size)]
        self._chunks.extend(DocumentChunk(ticker.upper(), source, chunk, f"{ticker.upper()}:{len(self._chunks) + index}") for index, chunk in enumerate(chunks) if chunk)
        return len(chunks)

    def query(self, ticker: str, question: str, limit: int = 4) -> list[dict[str, str]]:
        query_terms = _terms(question)
        scored = []
        for chunk in self._chunks:
            if chunk.ticker != ticker.upper():
                continue
            score = sum(min(count, _terms(chunk.text)[term]) for term, count in query_terms.items())
            if score:
                scored.append((score, chunk))
        return [{"chunk_id": chunk.chunk_id, "source": chunk.source, "text": chunk.text} for _, chunk in sorted(scored, key=lambda value: value[0], reverse=True)[:limit]]


default_rag_index = LocalRagIndex()
