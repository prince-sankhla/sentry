"""Emergency / disaster procurement context detected by the risk engine."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class EmergencyProcurementPlugin(ContextPlugin):
    id = "emergency"
    name = "Emergency procurement"
    indicator_priority = {
        "single_bidder": 0,
        "high_value_direct_award": 0,
        "abnormal_value": 0,
        "high_value": 0,
        "suspicious_timing": 1,
        "award_clustering": 3,
    }

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        from app.services.risk_engine import _detect_context

        ctx = _detect_context(package)
        if ctx.emergency or ctx.disaster:
            signal = next(
                (s for s in ctx.signals if "emergency" in s or "disaster" in s),
                "emergency/disaster language detected",
            )
            return LegitimateExplanation(
                explanation=self.name,
                evidence=f"The engine detected {signal} in the retrieved records.",
            )
        return None

    def verification_questions(self) -> list[str]:
        return ["Is there a recorded emergency declaration or sanction covering these tenders?"]

    def references(self) -> list[str]:
        return ["GFR 2017 Rule 166 / state emergency-procurement provisions."]
