"""
RAG wrapper — ChromaDB-based retrieval for the Local Experience Agent.

Responsibilities:
    - Initialize a persistent ChromaDB client (file-backed)
    - Embed queries using Gemini text-embedding-004
    - Retrieve top-k chunks per destination
    - Return empty list gracefully when no matches exist

The embedding call is isolated here so a provider swap only touches
one file.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from manzil.tools import cache

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy ChromaDB import — the package may not be installed in all envs
# ---------------------------------------------------------------------------

try:
    import chromadb
    from chromadb.config import Settings

    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    chromadb = None  # type: ignore

# ---------------------------------------------------------------------------
# Lazy Gemini embedding import
# ---------------------------------------------------------------------------

_CLIENT_READY = False


def _ensure_embedding_client():
    global _CLIENT_READY
    if _CLIENT_READY:
        return
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Required for text-embedding-004."
        )
    _CLIENT_READY = True


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Call Gemini text-embedding-004. Caches by content hash."""
    _ensure_embedding_client()

    # Check cache first
    results: List[Optional[List[float]]] = [None] * len(texts)
    missing_indices = []
    missing_texts = []

    for i, text in enumerate(texts):
        key = cache.stable_key({"text": text, "model": "text-embedding-004"})
        cached = cache.get("embedding", key)
        if cached is not None:
            results[i] = cached["vector"]
        else:
            missing_indices.append(i)
            missing_texts.append(text)

    if missing_texts:
        import google.generativeai as genai  # noqa: WPS433

        # Batch embedding — Gemini supports up to 100 per request
        batch_size = 100
        for batch_start in range(0, len(missing_texts), batch_size):
            batch = missing_texts[batch_start : batch_start + batch_size]
            resp = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
            )
            vectors = resp.get("embedding", [])
            for offset, vec in enumerate(vectors):
                idx = missing_indices[batch_start + offset]
                results[idx] = vec
                key = cache.stable_key(
                    {"text": missing_texts[batch_start + offset], "model": "text-embedding-004"}
                )
                cache.set("embedding", key, {"vector": vec})

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# RAG retrieval
# ---------------------------------------------------------------------------

_COLLECTION_NAME = "manzil_local_corpus"
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "chroma_db"


def _get_client():
    if not _CHROMA_AVAILABLE:
        raise RuntimeError(
            "chromadb is not installed. Run: pip install chromadb"
        )
    return chromadb.PersistentClient(
        path=str(_DB_PATH),
        settings=Settings(anonymized_telemetry=False),
    )


def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(
    destination_id: str,
    query_text: str,
    k: int = 5,
) -> List[Dict]:
    """
    Retrieve up to `k` chunks relevant to `query_text` for the given
    destination. Returns an empty list if the destination has no indexed
    content or if ChromaDB is unavailable.

    Each returned chunk is a dict:
        {
            "text": str,
            "source": str,       # file path relative to data/local_corpus/
            "destination_id": str,
            "distance": float,
        }
    """
    if not _CHROMA_AVAILABLE:
        log.warning("chromadb not available; returning empty retrieval")
        return []

    try:
        collection = _get_collection()
    except Exception as exc:
        log.warning("ChromaDB collection failed: %s", exc)
        return []

    # Embed the query
    try:
        vectors = _embed_texts([query_text])
        if not vectors:
            return []
        query_vector = vectors[0]
    except Exception as exc:
        log.warning("Embedding failed: %s", exc)
        return []

    # Query with destination filter
    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where={"destination_id": destination_id},
        )
    except Exception as exc:
        log.warning("ChromaDB query failed: %s", exc)
        return []

    out = []
    if not results.get("ids"):
        return out

    ids = results["ids"][0]
    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    for i, doc_id in enumerate(ids):
        meta = metadatas[i] if metadatas else {}
        out.append(
            {
                "text": documents[i] if documents else "",
                "source": meta.get("source", ""),
                "destination_id": meta.get("destination_id", destination_id),
                "distance": float(distances[i]) if distances else 0.0,
            }
        )

    return out


def add_documents(
    destination_id: str,
    documents: List[str],
    sources: List[str],
) -> None:
    """
    Add documents to the ChromaDB collection for a destination.
    Used by `scripts/build_rag_index.py`.
    """
    if not _CHROMA_AVAILABLE:
        raise RuntimeError("chromadb not installed")

    if len(documents) != len(sources):
        raise ValueError("documents and sources must have same length")

    collection = _get_collection()

    # Generate deterministic ids
    ids = []
    for i, (doc, src) in enumerate(zip(documents, sources)):
        h = hashlib.sha256(f"{destination_id}::{src}::{i}::{doc}".encode()).hexdigest()[:16]
        ids.append(h)

    # Embed in batches
    vectors = _embed_texts(documents)

    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=[
            {"destination_id": destination_id, "source": src}
            for src in sources
        ],
    )


__all__ = ["retrieve", "add_documents"]
