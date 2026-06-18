"""
BaseAgent contract.

Every specialist agent inherits from this. The contract enforces the
discipline from section 6 of the tech sketch: deterministic analysis first,
LLM only at the end to generate the natural-language argument.

Two modes are supported:
    Full LLM mode  — each agent calls the LLM to generate unique prose
    Efficient mode — each agent uses templated arguments (0 LLM calls)

The mode is controlled by:
    - Env var MANZIL_FULL_AGENT_LLM=true/false
    - Runtime toggle via set_full_llm_mode()

The contract:

    evaluate(candidate, query) -> AgentArgument
        ├─ _analyze            (deterministic, may call cached tool APIs)
        ├─ _check_blocker      (deterministic, returns Optional[str])
        ├─ _score              (deterministic, returns 0..10)
        ├─ _confidence         (deterministic, returns 0..1, default 1.0)
        └─ _produce_argument   (LLM or templated, parsed against LLMArgumentPayload)
              ├─ full mode + uses_llm=True   →  _build_argue_prompt + llm.complete_json
              ├─ efficient mode + uses_llm=True → _templated_argument (0 calls)
              └─ uses_llm=False  →  _canned_argument   (Phase-1 stubs)

If the LLM call raises `LLMParseError`, we fall back to a deterministic
argument with `confidence=0` and a single concern noting the failure.
The system never crashes mid-debate.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from manzil import llm
from manzil.llm import LLMParseError, Model
from manzil.schemas import (
    AgentArgument,
    LLMArgumentPayload,
    RouteCandidate,
    UserQuery,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global mode flag
# ---------------------------------------------------------------------------

_USE_FULL_LLM: bool = os.environ.get("MANZIL_FULL_AGENT_LLM", "false").lower() == "true"


def set_full_llm_mode(enabled: bool) -> None:
    """Toggle between Full LLM and Efficient modes at runtime."""
    global _USE_FULL_LLM
    _USE_FULL_LLM = enabled
    log.info("Agent mode set to: %s", "Full LLM" if enabled else "Efficient")


def is_full_llm_mode() -> bool:
    """Return True if agents should use LLM for argument generation."""
    return _USE_FULL_LLM


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class BaseAgent(ABC):
    """Abstract base for every specialist agent."""

    # --- Class-level configuration (subclass overrides) ---------------------
    name: str = ""
    uses_llm: bool = True
    llm_model: Model = Model.FLASH_LITE
    llm_temperature: float = 0.2

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def evaluate(self, candidate: RouteCandidate, query: UserQuery) -> AgentArgument:
        analysis = self._analyze(candidate, query)
        blocker = self._check_blocker(analysis, candidate, query)
        score = float(self._score(analysis, candidate, query))
        confidence = float(self._confidence(analysis, candidate, query))

        try:
            if _USE_FULL_LLM and self.uses_llm:
                payload = self._produce_argument(analysis, score, candidate, query)
            elif self.uses_llm:
                payload = self._templated_argument(analysis, score, candidate, query)
            else:
                payload = self._canned_argument(analysis, score, candidate, query)
            reasons = list(payload.reasons)
            concerns = list(payload.concerns)
        except LLMParseError as exc:
            log.warning(
                "%s: argument generation failed (%s) — falling back to deterministic",
                self.name,
                exc,
            )
            reasons = []
            concerns = [
                f"({self.name}: argument-generation failed; using deterministic score only)"
            ]
            confidence = 0.0

        return AgentArgument(
            agent_name=self.name,
            candidate_id=candidate.candidate_id,
            score=_clamp(score, 0.0, 10.0),
            supporting_reasons=reasons,
            concerns=concerns,
            hard_blocker=blocker,
            confidence=_clamp(confidence, 0.0, 1.0),
            raw_data=self._serialize_analysis(analysis),
        )

    # ------------------------------------------------------------------
    # Argument production
    # ------------------------------------------------------------------

    def _produce_argument(
        self,
        analysis: Any,
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> LLMArgumentPayload:
        if self.uses_llm:
            prompt = self._build_argue_prompt(analysis, score, candidate, query)
            system = self._system_instruction()
            return llm.complete_json(
                prompt,
                LLMArgumentPayload,
                model=self.llm_model,
                temperature=self.llm_temperature,
                system=system,
            )
        return self._canned_argument(analysis, score, candidate, query)

    def _system_instruction(self) -> Optional[str]:
        return (
            f"You are the {self.name} for a Pakistan travel-planning system. "
            "Reply with ONLY a JSON object matching the schema "
            '{"reasons": [string, ...], "concerns": [string, ...]}. '
            "Each item is a short bullet (max 25 words). "
            "Cite the data you are given; do not invent facts. "
            "If a fact is missing, say so rather than guessing."
        )

    # ------------------------------------------------------------------
    # Templated argument boilerplate (efficient mode)
    # ------------------------------------------------------------------

    def _templated_argument(
        self,
        analysis: Any,
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> LLMArgumentPayload:
        """
        Build a conversational argument without LLM calls.
        Subclasses override _templated_reasons and _templated_concerns.
        """
        reasons = self._templated_reasons(analysis, score, candidate, query)
        concerns = self._templated_concerns(analysis, score, candidate, query)

        # Fallbacks
        if not reasons:
            reasons.append(f"Overall {self.name} score: {score:.1f}/10.")
        if not concerns and score < 7.0:
            concerns.append(
                f"{self.name} conditions are moderate — review details before booking."
            )

        return LLMArgumentPayload(reasons=reasons[:3], concerns=concerns[:3])

    def _templated_reasons(
        self, analysis: Any, score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        """Return supporting reasons for efficient mode. Override in subclass."""
        return []

    def _templated_concerns(
        self, analysis: Any, score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        """Return concerns for efficient mode. Override in subclass."""
        return []

    # ------------------------------------------------------------------
    # Prompt helpers (reduce duplication in _build_argue_prompt)
    # ------------------------------------------------------------------

    def _prompt_header(
        self, candidate: RouteCandidate, query: UserQuery, score: float
    ) -> List[str]:
        """Shared header lines for every agent's argue prompt."""
        return [
            f"Candidate: {candidate.label}",
            f"Destinations: {' -> '.join(candidate.destinations)}",
            f"{self.name} deterministic score: {score:.1f}/10",
        ]

    def _json_instruction_lines(
        self, perspective: str, risk_label: str = "risks", fact_type: str = "facts"
    ) -> List[str]:
        """Shared JSON instruction footer for every agent's argue prompt."""
        return [
            "",
            "Produce a JSON object with exactly two keys:",
            '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
            f"              from a {perspective} perspective.",
            '  "concerns": 1-3 short bullets (<=25 words each) flagging '
            f"{risk_label}.",
            "",
            f"Cite the data above. Do not invent {fact_type}. "
            "Reply with ONLY the JSON.",
        ]

    # ------------------------------------------------------------------
    # Helpers (override-able by subclasses)
    # ------------------------------------------------------------------

    def _confidence(
        self, analysis: Any, candidate: RouteCandidate, query: UserQuery
    ) -> float:
        return 1.0

    def _serialize_analysis(self, analysis: Any) -> Dict[str, Any]:
        if isinstance(analysis, dict):
            return analysis
        if hasattr(analysis, "model_dump"):
            return analysis.model_dump(mode="json")
        return {"_repr": repr(analysis)}

    # ------------------------------------------------------------------
    # Abstract — every subclass must implement these
    # ------------------------------------------------------------------

    @abstractmethod
    def _analyze(self, candidate: RouteCandidate, query: UserQuery) -> Any: ...

    @abstractmethod
    def _check_blocker(
        self, analysis: Any, candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]: ...

    @abstractmethod
    def _score(
        self, analysis: Any, candidate: RouteCandidate, query: UserQuery
    ) -> float: ...

    # ------------------------------------------------------------------
    # Full LLM mode — real agents override
    # ------------------------------------------------------------------

    def _build_argue_prompt(
        self,
        analysis: Any,
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> str:
        raise NotImplementedError(
            f"{self.__class__.__name__} has uses_llm=True but did not "
            "implement _build_argue_prompt"
        )

    # ------------------------------------------------------------------
    # Stub mode — stubs override; real agents do not.
    # ------------------------------------------------------------------

    def _canned_argument(
        self,
        analysis: Any,
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> LLMArgumentPayload:
        raise NotImplementedError(
            f"{self.__class__.__name__} has uses_llm=False but did not "
            "implement _canned_argument"
        )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


__all__ = ["BaseAgent", "set_full_llm_mode", "is_full_llm_mode"]
