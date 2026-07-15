"""Context Plugin interface — one plugin per legitimate procurement context.

A Context Plugin encapsulates everything SENTRY knows about ONE benign
explanation for a deterministic finding (financial year-end, framework
agreement, emergency procurement, …). The Evidence Challenge engine knows
nothing about any specific context — it only speaks this interface.

Contract:
  * Plugins are READ-ONLY. They receive the finished package and finding and
    must never modify indicators, severities, scores, or evidence.
  * Plugins never invent. ``collect_evidence`` returns an explanation ONLY when
    deterministic evidence for it exists in the package; otherwise ``None``.
  * ``indicator_priority`` declares which indicator types the context can
    logically apply to, and in what display order per indicator — so a finding
    is never challenged with an explanation that could not apply to it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2


class ContextPlugin(ABC):
    """Base class for all procurement-context plugins."""

    #: Stable machine id, e.g. ``"fy_end"``.
    id: str = ""
    #: Human-readable explanation label shown to the investigator.
    name: str = ""
    #: indicator id -> ordering position for that indicator. Presence in this
    #: mapping IS applicability; the position preserves a deterministic,
    #: investigator-curated presentation order per finding.
    indicator_priority: dict[str, int] = {}

    def applies_to(self, indicator_id: str) -> bool:
        """Whether this context can logically explain the given indicator type."""
        return indicator_id in self.indicator_priority

    @abstractmethod
    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        """Return the explanation ONLY if deterministic evidence exists in the
        package; ``None`` otherwise. Must not mutate ``package`` or ``finding``."""

    @abstractmethod
    def verification_questions(self) -> list[str]:
        """The questions that would eliminate (or confirm) this explanation."""

    def references(self) -> list[str]:
        """Authoritative procurement guidance backing this context (documentation;
        not serialized into the challenge output)."""
        return []
