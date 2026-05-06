"""
One-time script: chunk every file in `data/local_corpus/`, embed with
local ONNX all-MiniLM-L6-v2, and persist to ChromaDB.

Idempotent: skips already-indexed files by checking content hash.

Usage:
    python scripts/build_rag_index.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path

from manzil.tools import rag

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "local_corpus"
_INDEX_TRACKER = Path(__file__).resolve().parent.parent / "chroma_db" / ".indexed_files.json"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_tracker() -> dict:
    if _INDEX_TRACKER.exists():
        with _INDEX_TRACKER.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_tracker(data: dict) -> None:
    _INDEX_TRACKER.parent.mkdir(parents=True, exist_ok=True)
    with _INDEX_TRACKER.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _chunk_text(text: str, max_words: int = 200) -> list[str]:
    """Simple word-count chunker."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
    return chunks


def main() -> int:
    if not _DATA_DIR.exists():
        log.error("Local corpus directory not found: %s", _DATA_DIR)
        return 1

    tracker = _load_tracker()
    indexed_count = 0
    skipped_count = 0

    for dest_dir in sorted(_DATA_DIR.iterdir()):
        if not dest_dir.is_dir():
            continue
        dest_id = dest_dir.name

        for md_file in sorted(dest_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            h = _content_hash(text)
            tracker_key = f"{dest_id}/{md_file.name}"

            if tracker.get(tracker_key) == h:
                skipped_count += 1
                continue

            chunks = _chunk_text(text)
            sources = [f"{dest_id}/{md_file.name}#chunk{i}" for i in range(len(chunks))]

            if chunks:
                rag.add_documents(dest_id, chunks, sources)
                tracker[tracker_key] = h
                indexed_count += 1
                log.info("Indexed %s (%d chunks)", tracker_key, len(chunks))

    _save_tracker(tracker)
    log.info(
        "Done. Indexed %d files, skipped %d (already up-to-date).",
        indexed_count,
        skipped_count,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
