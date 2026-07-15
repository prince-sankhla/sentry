"""Correction / corrigendum notice present in the retrieved records."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class CorrigendumPlugin(ContextPlugin):
    id = "corrigendum"
    name = "Correction notice explains the timeline"
    indicator_priority = {"suspicious_timing": 0}

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        from app.services.risk_engine import _detect_context

        ctx = _detect_context(package)
        if ctx.correction_notice:
            return LegitimateExplanation(
                explanation=self.name,
                evidence="A correction/corrigendum notice is present in the retrieved records.",
            )
        return None

    def verification_questions(self) -> list[str]:
        return ["Does the corrigendum on record legitimately explain the compressed timeline?"]

    def references(self) -> list[str]:
        return ["NIC eProcurement corrigendum publication rules — schedule changes must be notified."]
