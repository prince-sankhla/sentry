"""Large national supplier — awards from multiple distinct buyers in-package."""

from __future__ import annotations

from collections import defaultdict

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register


@register
class NationalSupplierPlugin(ContextPlugin):
    id = "national_supplier"
    name = "Large national supplier winning on competitive strength"
    indicator_priority = {
        "repeat_supplier": 1,
        "buyer_concentration": 1,
        "award_clustering": 2,
    }

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        supplier_buyers: dict[str, set[str]] = defaultdict(set)
        for r in package.records:
            buyer = (r.tender.procuring_entity or "").strip()
            for a in r.awards:
                if a.company_name and buyer:
                    supplier_buyers[a.company_name].add(buyer)
        for supplier, buyers in supplier_buyers.items():
            if len(buyers) >= 2:
                return LegitimateExplanation(
                    explanation=self.name,
                    evidence=f"{supplier} holds awards from {len(buyers)} distinct procuring entities in this package.",
                )
        return None

    def verification_questions(self) -> list[str]:
        return ["Do bid registers show other qualified bidders competing and losing to this supplier?"]

    def references(self) -> list[str]:
        return ["OCP red-flag guidance — repeat wins require bid-participation context before inference."]
