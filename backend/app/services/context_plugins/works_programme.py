"""Multi-package works programme — one sanctioned scheme delivered as lots."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class WorksProgrammePlugin(ContextPlugin):
    id = "works_programme"
    name = "Multi-package works programme (one sanctioned scheme delivered as lots)"
    indicator_priority = {"contract_fragmentation": 0}

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        # Distinct work scopes across the finding's batch — consistent with one
        # sanctioned programme delivered as separate lots (e.g. ward-wise works).
        ref_set = set(finding.supporting_records)
        titles = {
            (r.tender.title or "").strip().casefold()
            for r in package.records
            if r.tender.reference_number in ref_set and (r.tender.title or "").strip()
        }
        in_batch = sum(1 for r in package.records if r.tender.reference_number in ref_set)
        if in_batch >= 3 and len(titles) == in_batch:
            return LegitimateExplanation(
                explanation=self.name,
                evidence=f"All {in_batch} tenders in the batch describe distinct works/locations (no duplicated scope).",
                records=list(finding.supporting_records)[:10],
            )
        return None

    def verification_questions(self) -> list[str]:
        return [
            "Same funding source?",
            "Same DPR?",
            "Same administrative approval?",
            "Same work package?",
            "Same evaluation committee?",
            "Same sanction note?",
            "Same estimate file?",
        ]

    def references(self) -> list[str]:
        return ["CVC guidance on splitting of works vis-à-vis delegation-of-power thresholds."]
