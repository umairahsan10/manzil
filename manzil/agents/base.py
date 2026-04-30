"""
BaseAgent contract.

Every specialist agent inherits from this. The contract enforces the
discipline from section 6 of the tech sketch: deterministic analysis first,
LLM only at the end to generate the natural-language argument.

The contract:

    evaluate(candidate, query) -> AgentArgument
        ├─ _analyze            (deterministic, may call cached tool APIs)
        ├─ _check_blocker      (deterministic, returns Optional[str])
        ├─ _score              (deterministic, returns 0..10)
        ├─ _confidence         (deterministic, returns 0..1, default 1.0)
        └─ _produce_argument   (LLM call, parsed against LLMArgumentPayload)
              ├─ uses_llm=True   →  _build_argue_prompt + llm.complete_json
              └─ uses_llm=False  →  _canned_argument   (Phase-1 stubs)

If the LLM call raises `LLMParseError`, we fall back to a deterministic
argument with `confidence=0` and a single concern noting the failure.
The system never crashes mid-debate.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from manzil import llm
from manzil.llm import LLMParseError, Model
from manzil.schemas import (
    AgentArgument,
    LLMArgumentPayload,
    RouteCandidate,
    UserQuery,
)

log = logging.getLogger(__name__)


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
            payload = self._produce_argument(analysis, score, candidate, query)
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
    # Argument production (split so stubs can skip the LLM cleanly)
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
    # Used only when uses_llm=True. Real agents override; stubs do not.
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
    # Used only when uses_llm=False. Stubs override; real agents do not.
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


__all__ = ["BaseAgent"]
