"""
LocalExperienceAgent — Phase 3 real agent (RAG-grounded).

Deterministic analysis:
    - Queries the RAG index via manzil.tools.rag.retrieve(destination_id, query_text, k=5)
    - Aggregates retrieved chunks
    - Scores by retrieval relevance + cultural-alignment against query.style_tags

Hard blockers:
    - NEVER blocks — Local Experience is enrichment, not safety.

Score:
    - Average retrieval relevance + cultural-alignment score.
    - If retrieval is empty for any destination, score that segment 0 and lower confidence.

LLM argument:
    - Quotes/paraphrases from retrieved chunks (food spots, viewpoints, photography hours).
    - If retrieval is empty, surfaces the gap honestly:
      "We don't have curated local content for X yet."
    - NEVER hallucinates places not in retrieved chunks.

Phase 5 addition: debug cache at .manzil_cache/local_retrievals.json
    logs every retrieval call for the RAG curation pass.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from manzil.agents.base import BaseAgent
from manzil.schemas import RouteCandidate, UserQuery
from manzil.tools import rag

_DEBUG_CACHE_PATH = Path(os.environ.get("MANZIL_CACHE_DIR", ".manzil_cache")) / "local_retrievals.json"


def _log_retrieval(dest_id: str, query_text: str, chunks: list, score: float) -> None:
    try:
        _DEBUG_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if _DEBUG_CACHE_PATH.exists():
            try:
                data = json.loads(_DEBUG_CACHE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        entry = {
            "destination_id": dest_id,
            "query_text": query_text,
            "n_chunks": len(chunks),
            "avg_distance": round(sum(c["distance"] for c in chunks) / max(1, len(chunks)), 4) if chunks else None,
            "score": round(score, 3),
        }
        key = f"{dest_id}::{query_text[:50]}"
        data[key] = entry
        _DEBUG_CACHE_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (OSError, json.JSONEncodeError):
        pass


class LocalExperienceAgent(BaseAgent):
    name = "LocalAgent"
    uses_llm = True

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        user_styles = {s.lower() for s in query.style_tags}
        per_dest = []
        any_empty = False
        total_relevance = 0.0
        total_chunks = 0

        for dest_id in candidate.destinations:
            # Build a query text from style tags
            query_text = " ".join(query.style_tags) if query.style_tags else "local experiences food viewpoints culture"
            chunks = rag.retrieve(dest_id, query_text, k=5)

            if not chunks:
                any_empty = True
                per_dest.append(
                    {
                        "id": dest_id,
                        "chunks": [],
                        "chunk_count": 0,
                        "avg_relevance": 0.0,
                        "style_alignment": 0.0,
                    }
                )
                _log_retrieval(dest_id, query_text, [], 0.0)
                continue

            # Compute avg relevance (lower distance = higher relevance)
            avg_dist = sum(c["distance"] for c in chunks) / len(chunks)
            relevance = max(0.0, 1.0 - avg_dist)  # normalize roughly 0-1

            # Style alignment: count style tag mentions in chunks
            chunk_text = " ".join(c["text"].lower() for c in chunks)
            matched_styles = [s for s in user_styles if s in chunk_text]
            alignment = len(matched_styles) / max(1, len(user_styles)) if user_styles else 0.5

            _log_retrieval(dest_id, query_text, chunks, relevance)

            per_dest.append(
                {
                    "id": dest_id,
                    "chunks": [
                        {"text": c["text"][:300], "source": c["source"], "distance": round(c["distance"], 3)}
                        for c in chunks
                    ],
                    "chunk_count": len(chunks),
                    "avg_relevance": round(relevance, 3),
                    "style_alignment": round(alignment, 3),
                    "matched_styles": matched_styles,
                }
            )

            total_relevance += relevance
            total_chunks += 1

        avg_relevance = total_relevance / max(1, total_chunks)

        return {
            "user_style_tags": sorted(user_styles),
            "per_destination": per_dest,
            "avg_relevance": round(avg_relevance, 3),
            "any_empty_retrieval": any_empty,
        }

    def _check_blocker(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]:
        return None  # Local experience never blocks

    def _score(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        per_dest = analysis.get("per_destination", [])
        if not per_dest:
            return 5.0

        scores = []
        for d in per_dest:
            rel = d.get("avg_relevance", 0.0)
            align = d.get("style_alignment", 0.0)
            # Combine relevance and alignment
            s = (rel * 5.0) + (align * 5.0)
            scores.append(s)

        return sum(scores) / len(scores)

    def _confidence(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        if analysis.get("any_empty_retrieval", False):
            return 0.5
        return 1.0

    def _build_argue_prompt(
        self,
        analysis: Dict[str, Any],
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> str:
        lines = [
            f"Candidate: {candidate.label}",
            f"Destinations: {' -> '.join(candidate.destinations)}",
            f"User style tags: {', '.join(analysis['user_style_tags']) or 'none'}",
            f"LocalAgent deterministic score: {score:.1f}/10",
            "",
        ]

        for d in analysis.get("per_destination", []):
            lines.append(f"--- {d['id']} ---")
            if d.get("chunk_count", 0) == 0:
                lines.append("NO curated local content retrieved for this destination.")
            else:
                lines.append(f"Retrieved {d['chunk_count']} chunks. " f"Relevance: {d['avg_relevance']}, Alignment: {d['style_alignment']}")
                for c in d.get("chunks", []):
                    lines.append(f"  [{c['source']}] {c['text'][:200]}...")

        lines.extend(
            [
                "",
                "Produce a JSON object with exactly two keys:",
                '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
                "              from a local-experience perspective. Quote or paraphrase retrieved chunks.",
                '  "concerns": 1-3 short bullets (<=25 words each) noting gaps or risks.',
                "",
                "CRITICAL RULES:",
                "- If retrieval is empty for a destination, say so honestly: "
                "'We don't have curated local content for X yet.'",
                "- NEVER mention a place, restaurant, or viewpoint that is not in the retrieved chunks above.",
                "- Do not hallucinate. Reply with ONLY the JSON.",
            ]
        )
        return "\n".join(lines)

    def _templated_reasons(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        reasons = []
        per_dest = analysis.get("per_destination", [])
        matched = []
        empty = []
        high_rel = []

        for d in per_dest:
            dest_id = d.get("id", "unknown")
            if d.get("chunk_count", 0) == 0:
                empty.append(dest_id)
                continue
            if d.get("avg_relevance", 0) > 0.5:
                high_rel.append(dest_id)
            matched_styles = d.get("matched_styles", [])
            if matched_styles:
                matched.append(f"{dest_id} ({', '.join(matched_styles[:2])})")

        if matched:
            reasons.append(f"Strong style alignment found in {', '.join(matched[:2])}.")
        if high_rel:
            reasons.append(f"High-quality local content retrieved for {', '.join(high_rel[:2])}.")
        if not empty and per_dest:
            reasons.append("Curated local content available for all destinations on this route.")

        return reasons

    def _templated_concerns(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        concerns = []
        per_dest = analysis.get("per_destination", [])
        user_styles = analysis.get("user_style_tags", [])
        empty = []
        matched = []

        for d in per_dest:
            dest_id = d.get("id", "unknown")
            if d.get("chunk_count", 0) == 0:
                empty.append(dest_id)
                continue
            matched_styles = d.get("matched_styles", [])
            if matched_styles:
                matched.append(dest_id)

        if empty:
            concerns.append(f"Limited curated content for {', '.join(empty[:2])} — local tips may be sparse.")
        if not matched and user_styles:
            concerns.append(f"Style tags ({', '.join(user_styles[:2])}) not strongly matched in retrieved content.")
        if analysis.get("any_empty_retrieval"):
            concerns.append("Some destinations lack curated local content in our database.")

        return concerns


__all__ = ["LocalExperienceAgent"]
