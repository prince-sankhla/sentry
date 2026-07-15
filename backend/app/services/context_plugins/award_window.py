"""Award not yet due — closed tenders still within the publication window."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class AwardWindowPlugin(ContextPlugin):
    id = "award_window"
    name = "Award not yet due for publication"
    indicator_priority = {"missing_award_data": 0}

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        from app.services.investigation_indicators import award_timing_status

        try:
            status = award_timing_status(package)
        except Exception:
            return None
        pending = status.get("pending") or []
        overdue = status.get("overdue") or []
        if pending and not overdue and status.get("as_of") is not None:
            return LegitimateExplanation(
                explanation=self.name,
                evidence=(
                    f"{len(pending)} closed tender(s) are still within the expected award-publication "
                    f"window as of {status['as_of']}."
                ),
                records=[r.tender.reference_number for r in pending][:10],
            )
        return None

    def verification_questions(self) -> list[str]:
        return ["Re-check the portal results section once the award-publication window has elapsed?"]

    def references(self) -> list[str]:
        return ["NIC eProcurement award-publication lifecycle (results section timing)."]
