"""Financial year-end procurement activity (Indian FY ends 31 March)."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class FinancialYearEndPlugin(ContextPlugin):
    id = "fy_end"
    name = "Financial year-end procurement activity"
    indicator_priority = {
        "award_clustering": 0,
        "contract_fragmentation": 1,
        "repeat_supplier": 2,
    }

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        award_dates = [a.award_date for r in package.records for a in r.awards if a.award_date]
        fy_end = [d for d in award_dates if d.month in (2, 3)]
        if award_dates and fy_end and len(fy_end) * 2 >= len(award_dates):
            refs = [r.tender.reference_number for r in package.records
                    if any(a.award_date and a.award_date.month in (2, 3) for a in r.awards)]
            return LegitimateExplanation(
                explanation=self.name,
                evidence=f"{len(fy_end)} of {len(award_dates)} award dates fall in February–March (Indian financial year-end).",
                records=refs[:10],
            )
        return None

    def verification_questions(self) -> list[str]:
        return [
            "Were the administrative approvals / sanction notes dated before the year-end window?",
            "Does this buyer's funding source lapse on 31 March (budget-head rules)?",
        ]

    def references(self) -> list[str]:
        return ["GFR 2017 — lapse of budget grants at financial year close (rush-of-expenditure guidance)."]
