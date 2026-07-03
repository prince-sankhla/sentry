from __future__ import annotations

import re

from app.connectors import SourceManager
from app.schemas.investigation_planner import InvestigationPlan, InvestigationPlanStep, InvestigationType


TYPE_KEYWORDS: dict[InvestigationType, tuple[str, ...]] = {
    "supplier": ("supplier", "vendor", "bidder", "contractor"),
    "buyer": ("buyer", "procuring entity", "purchaser", "agency"),
    "tender": ("tender", "rfp", "bid notice", "notice", "procurement id"),
    "director": ("director", "owner", "beneficial owner", "officer"),
    "contract": ("contract", "agreement", "award", "po number", "work order"),
    "ministry": ("ministry", "department", "authority", "municipality"),
    "location": ("location", "district", "city", "state", "country", "region"),
    "company": ("company", "firm", "limited", "ltd", "private limited", "inc", "llp", "corp"),
}

MODULE_ORDER: dict[InvestigationType, list[str]] = {
    "company": ["company_connectors", "awards", "tenders", "suppliers", "buyers", "graph", "timeline", "procurement_intelligence", "evidence"],
    "supplier": ["company_connectors", "awards", "tenders", "buyers", "graph", "timeline", "procurement_intelligence", "evidence"],
    "buyer": ["buyer_connectors", "tenders", "awards", "suppliers", "graph", "timeline", "procurement_intelligence", "evidence"],
    "tender": ["tender_connectors", "awards", "documents", "suppliers", "buyer", "graph", "timeline", "procurement_intelligence", "evidence"],
    "director": ["entity_resolution", "company_connectors", "suppliers", "awards", "graph", "timeline", "evidence"],
    "contract": ["tender_connectors", "awards", "documents", "suppliers", "buyer", "graph", "timeline", "procurement_intelligence", "evidence"],
    "ministry": ["buyer_connectors", "tenders", "awards", "suppliers", "graph", "timeline", "procurement_intelligence", "evidence"],
    "location": ["source_connectors", "tenders", "buyers", "suppliers", "awards", "graph", "timeline", "procurement_intelligence", "evidence"],
}

ACTION_BY_MODULE = {
    "awards": "Search awards",
    "buyer": "Search buyer",
    "buyer_connectors": "Search buyer connectors",
    "buyers": "Search buyers",
    "company_connectors": "Search company connectors",
    "documents": "Search documents",
    "entity_resolution": "Resolve entity aliases",
    "evidence": "Merge evidence",
    "graph": "Search relationship graph",
    "procurement_intelligence": "Load procurement intelligence",
    "source_connectors": "Search source connectors",
    "suppliers": "Search suppliers",
    "tender_connectors": "Search tender connectors",
    "tenders": "Search tenders",
    "timeline": "Search timeline",
}

CONNECTOR_MODULES = {"buyer_connectors", "company_connectors", "source_connectors", "tender_connectors"}


class InvestigationPlanner:
    def __init__(self, source_manager: SourceManager | None = None) -> None:
        self.source_manager = source_manager or SourceManager()

    def build_plan(self, query: str, source_names: list[str] | None = None) -> InvestigationPlan:
        normalized_query = _clean_query(query)
        investigation_type, confidence = self.detect_type(normalized_query)
        connectors = self._select_connectors(source_names)
        modules = MODULE_ORDER[investigation_type]
        steps = self._build_steps(
            query=normalized_query,
            investigation_type=investigation_type,
            modules=modules,
            connectors=connectors,
        )
        return InvestigationPlan(
            query=normalized_query,
            investigation_type=investigation_type,
            confidence=confidence,
            connectors=connectors,
            modules=modules,
            steps=steps,
        )

    def detect_type(self, query: str) -> tuple[InvestigationType, float]:
        lowered = query.casefold()
        scores: dict[InvestigationType, int] = {investigation_type: 0 for investigation_type in TYPE_KEYWORDS}
        for investigation_type, keywords in TYPE_KEYWORDS.items():
            scores[investigation_type] += sum(2 for keyword in keywords if keyword in lowered)

        if re.search(r"\b[A-Z]{2,8}[:/-][A-Z0-9][A-Z0-9./-]{4,}\b", query):
            scores["tender"] += 4
        if re.search(r"\b(contract|agreement|award)\s*(no\.?|number|id)?\s*[:#-]?\s*[A-Z0-9./-]{4,}\b", lowered):
            scores["contract"] += 4
        if re.search(r"\b(ministry|department of|municipal|authority)\b", lowered):
            scores["ministry"] += 3
        if re.search(r"\b(district|province|state of|city of)\b", lowered):
            scores["location"] += 3

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        if best_score == 0:
            return "company", 0.45
        confidence = min(0.95, 0.55 + (best_score * 0.1))
        return best_type, confidence

    def _select_connectors(self, source_names: list[str] | None) -> list[str]:
        available = self.source_manager.connector_names()
        if not source_names:
            return available
        requested = {source_name.strip() for source_name in source_names if source_name.strip()}
        return [source_name for source_name in available if source_name in requested]

    def _build_steps(
        self,
        *,
        query: str,
        investigation_type: InvestigationType,
        modules: list[str],
        connectors: list[str],
    ) -> list[InvestigationPlanStep]:
        steps: list[InvestigationPlanStep] = []
        previous_module: str | None = None
        for index, module in enumerate(modules, start=1):
            step_connectors = connectors if module in CONNECTOR_MODULES else []
            steps.append(
                InvestigationPlanStep(
                    order=index,
                    module=module,
                    action=ACTION_BY_MODULE[module],
                    connectors=step_connectors,
                    inputs={
                        "query": query,
                        "investigation_type": investigation_type,
                    },
                    depends_on=[previous_module] if previous_module else [],
                )
            )
            previous_module = module
        return steps


def _clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()
