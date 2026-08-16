"""Pydantic-AI harness that actually spawns the pipeline's agents.

The signal-extractor sub-agents and the analyst reviewers are launched as
Pydantic-AI `Agent`s with typed (pydantic) outputs, running on OpenAI. When
`OPENAI_API_KEY` is set they make real model calls; with no key (or if the
harness isn't installed) they fall back to the deterministic behaviour, so
offline runs and tests are unchanged.

Per the runbook's authority split the model only produces *reasoning and
verdicts* — the forecast number is always computed by the deterministic engine
from verified observations, never written by the model.
"""

from __future__ import annotations

import os

try:  # the pydantic harness + OpenAI provider (assumed present in a live run)
    from pydantic import BaseModel
    from pydantic_ai import Agent

    _HARNESS_AVAILABLE = True
except Exception:  # keep the package importable offline / in tests
    _HARNESS_AVAILABLE = False

    class BaseModel:  # minimal stand-in so the output types below still define
        pass


DEFAULT_MODEL = "openai:gpt-5.6-sol"

SUBAGENT_SYSTEM = (
    "You are a signal-extraction sub-agent in a forecasting pipeline. Given a source quotation, "
    "state what value it supports for the metric and whether that value is grounded strictly in the "
    "quotation (never trained knowledge). Be concise."
)
ANALYST_SYSTEM = (
    "You are an analyst reviewing a forecast. Review whether the reasoning and the evidence chain "
    "support the figure, and whether it is supported. Be concise and specific."
)


class SubAgentExtraction(BaseModel):
    """Typed output of a signal-extractor sub-agent."""

    value_summary: str
    reasoning: str
    grounded: bool


class AnalystReview(BaseModel):
    """Typed output of an analyst reviewer."""

    review: str
    supported: bool


class AgentHarness:
    """Spawns the pipeline's agents via Pydantic AI on OpenAI."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("FORECAST_AGENT_MODEL", DEFAULT_MODEL)
        self.spawned = 0
        self._subagent = None
        self._analyst = None

    @property
    def enabled(self) -> bool:
        return _HARNESS_AVAILABLE and bool(os.environ.get("OPENAI_API_KEY"))

    def _ensure(self) -> None:
        if self._subagent is None:
            self._subagent = Agent(self.model, output_type=SubAgentExtraction, system_prompt=SUBAGENT_SYSTEM)
            self._analyst = Agent(self.model, output_type=AnalystReview, system_prompt=ANALYST_SYSTEM)

    def extract(self, prompt: str) -> SubAgentExtraction | None:
        """Spawn a signal-extractor sub-agent. Returns its typed output, or None when disabled/on error."""
        if not self.enabled:
            return None
        try:
            self._ensure()
            output = self._subagent.run_sync(prompt).output
            self.spawned += 1
            return output
        except Exception:
            return None

    def review(self, prompt: str) -> AnalystReview | None:
        """Spawn an analyst reviewer. Returns its typed output, or None when disabled/on error."""
        if not self.enabled:
            return None
        try:
            self._ensure()
            output = self._analyst.run_sync(prompt).output
            self.spawned += 1
            return output
        except Exception:
            return None
