"""Framework agreement / rate contract detected in the tender text."""

from __future__ import annotations

from app.schemas.evidence_challenge import LegitimateExplanation
from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2
from app.services.context_plugins.base import ContextPlugin
from app.services.context_plugins.registry import register

_FRAMEWORK_TERMS = ("framework agreement", "rate contract", "empanel", "annual maintenance contract")


@register
class FrameworkAgreementPlugin(ContextPlugin):
    id = "framework"
    name = "Framework agreement / rate contract"
    indicator_priority = {
        "repeat_supplier": 0,
        "buyer_concentration": 0,
        "supplier_concentration": 0,
        "award_clustering": 1,
        "single_bidder": 1,
    }

    def collect_evidence(
        self, package: InvestigationPackage, finding: RiskIndicatorV2
    ) -> LegitimateExplanation | None:
        for r in package.records:
            blob = f"{r.tender.title or ''} {r.tender.description or ''}".casefold()
            for term in _FRAMEWORK_TERMS:
                if term in blob:
                    return LegitimateExplanation(
                        explanation=self.name,
                        evidence=f"The term “{term}” appears in tender {r.tender.reference_number}.",
                        records=[r.tender.reference_number],
                    )
        return None

    def verification_questions(self) -> list[str]:
        return ["Is a framework agreement or rate contract cited in the award / contract file?"]

    def references(self) -> list[str]:
        return ["Manual for Procurement of Goods 2024 — rate contracts / framework agreements."]
