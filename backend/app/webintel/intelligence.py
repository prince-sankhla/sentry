"""Procurement Intelligence assembler.

Turns stored :class:`WebEvidence` rows into analyst-grade, fully-provenanced,
clustered intelligence. This is the read side of the Procurement Intelligence
Engine: every item it emits carries a source, evidence type, confidence,
publication date, original URL, citation, summary, and its related
entities/tenders/contracts/organizations/investigations — grouped into the seven
investigation clusters.

Nothing here fabricates: confidence is a deterministic function of source
authority + verifiability + specificity + recency, the citation is composed from
stored provenance, and the summary is drawn from the page's own extracted
signals. The backend proves; it never invents.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.webintel.evidence_taxonomy import CLUSTERS, EvidenceClassification, classify_evidence
from app.webintel.models import WebEvidence, WebProcurementEvidence
from app.webintel.schemas import (
    EvidenceCluster,
    ProcurementIntelligenceItem,
    ProcurementIntelligenceResponse,
)
from app.webintel.source_authority import SourceClassification, classify_source, is_procurement_relevant
from app.webintel.utils import clean_whitespace

_CLUSTER_LABELS: dict[str, str] = {
    "contracts": "Contracts & Awards",
    "litigation": "Litigation & Arbitration",
    "audit": "Audit & Vigilance",
    "compliance": "Compliance & Debarment",
    "financial": "Financial & Regulatory",
    "news": "Procurement News",
    "government": "Government Records",
}


def confidence_for(
    source: SourceClassification,
    evidence: EvidenceClassification,
    proc: WebProcurementEvidence | None,
    *,
    has_publication_date: bool,
    retrieved_at: datetime | None,
) -> tuple[float, str]:
    """Deterministic 0-1 confidence + tier for one evidence item.

    Additive and explainable:
      * source authority (0-42): official portals/oversight rank highest
      * evidence specificity (0-20): a keyword-typed record beats a bare default
      * linkage (0-18): resolves to a known tender/company/award in our DB
      * verifiability (0-10): a publication date anchors the record in time
      * recency (0-10): recently retrieved evidence is more trustworthy
    """
    score = float(source.authority)  # 0..~48

    # specificity: strong keyword match => the type is well-supported
    score += min(20.0, evidence.score * 4.0)

    # linkage into structured procurement data
    if proc is not None:
        if proc.tender_id or proc.award_id:
            score += 12.0
        if proc.company_id:
            score += 6.0
        elif proc.contract_number or proc.tender_number:
            score += 4.0

    if has_publication_date:
        score += 10.0

    if retrieved_at is not None:
        now = datetime.now(timezone.utc)
        ret = retrieved_at if retrieved_at.tzinfo else retrieved_at.replace(tzinfo=timezone.utc)
        age_days = max(0, (now - ret).days)
        if age_days <= 30:
            score += 10.0
        elif age_days <= 180:
            score += 6.0
        elif age_days <= 365:
            score += 3.0

    confidence = max(0.0, min(1.0, score / 100.0))
    if confidence >= 0.75:
        tier = "high"
    elif confidence >= 0.5:
        tier = "medium"
    elif confidence >= 0.3:
        tier = "low"
    else:
        tier = "weak"
    return round(confidence, 2), tier


def _citation(evidence: WebEvidence, source: SourceClassification, evidence_cls: EvidenceClassification,
              publication_date: str | None) -> str:
    """Compose an analyst-grade, ready-to-paste citation from stored provenance."""
    parts: list[str] = []
    if evidence.title:
        parts.append(clean_whitespace(evidence.title))
    parts.append(source.label or evidence.source)
    parts.append(evidence_cls.evidence_type.replace("_", " "))
    if publication_date:
        parts.append(f"published {publication_date}")
    if evidence.retrieved_at:
        parts.append(f"retrieved {evidence.retrieved_at.date().isoformat()}")
    head = ". ".join(p for p in parts if p)
    return f"{head}. {evidence.url}".strip()


def _summary(evidence: WebEvidence, proc: WebProcurementEvidence | None,
             evidence_cls: EvidenceClassification) -> str:
    """A grounded one-line evidence summary from the page's own signals."""
    bits: list[str] = [evidence_cls.evidence_type.replace("_", " ").capitalize()]
    if proc is not None:
        if proc.government_buyer:
            bits.append(f"buyer {proc.government_buyer}")
        if proc.company_name:
            bits.append(f"supplier {proc.company_name}")
        if proc.contract_value is not None:
            unit = proc.currency or ""
            bits.append(f"value {unit} {proc.contract_value}".strip())
        if proc.tender_number:
            bits.append(f"tender {proc.tender_number}")
        elif proc.contract_number:
            bits.append(f"contract {proc.contract_number}")
    if len(bits) == 1 and evidence.title:
        bits.append(clean_whitespace(evidence.title)[:160])
    return "; ".join(bits)


def _related(proc: WebProcurementEvidence | None) -> dict[str, list[str]]:
    """Extract the five linkage lists from the stored procurement evidence."""
    if proc is None:
        return {k: [] for k in
                ("entities", "tenders", "contracts", "organizations", "investigations")}

    entities: list[str] = []
    for name in (proc.company_name, proc.normalized_company_name, proc.government_buyer):
        if name and name not in entities:
            entities.append(name)
    for name in (proc.related_companies or []):
        if name and name not in entities:
            entities.append(name)

    tenders = [v for v in (proc.tender_number, proc.tender_title) if v]
    contracts = [v for v in (proc.contract_number, proc.contract_title) if v]

    organizations: list[str] = []
    for name in (proc.organization, proc.government_buyer):
        if name and name not in organizations:
            organizations.append(name)

    # related_investigations: structured IDs we resolved this evidence to.
    investigations = [str(v) for v in (proc.tender_id, proc.company_id, proc.award_id) if v]

    return {
        "entities": entities[:12],
        "tenders": tenders[:8],
        "contracts": contracts[:8],
        "organizations": organizations[:8],
        "investigations": investigations,
    }


def build_intelligence_item(evidence: WebEvidence) -> ProcurementIntelligenceItem | None:
    """Assemble one fully-provenanced intelligence item, or None if inadmissible.

    Re-classifies the stored page so a source that later becomes inadmissible is
    dropped from intelligence output even if it was stored under older rules.
    """
    source = classify_source(evidence.url, title=evidence.title)
    if not source.admissible:
        return None
    # Content relevance gate: an admissible HOST is not enough — the page itself
    # must be procurement intelligence (rejects admissions/contact/marketing/
    # college pages even on allow-listed government or educational hosts).
    if not is_procurement_relevant(evidence.title, evidence.url, evidence.content):
        return None

    proc = evidence.procurement_evidence
    evidence_cls = classify_evidence(source, title=evidence.title, url=evidence.url, text=evidence.content)

    publication_date = None
    if proc is not None and proc.publication_date is not None:
        publication_date = proc.publication_date.isoformat()

    confidence, tier = confidence_for(
        source, evidence_cls, proc,
        has_publication_date=publication_date is not None,
        retrieved_at=evidence.retrieved_at,
    )
    related = _related(proc)

    return ProcurementIntelligenceItem(
        id=str(evidence.id),
        source=source.label or evidence.source,
        source_type=source.source_type,
        evidence_type=evidence_cls.evidence_type,
        cluster=evidence_cls.cluster,
        confidence=confidence,
        confidence_tier=tier,
        publication_date=publication_date,
        url=evidence.url,
        citation=_citation(evidence, source, evidence_cls, publication_date),
        evidence_summary=_summary(evidence, proc, evidence_cls),
        related_entities=related["entities"],
        related_tenders=related["tenders"],
        related_contracts=related["contracts"],
        related_organizations=related["organizations"],
        related_investigations=related["investigations"],
        matched_terms=list(evidence_cls.matched_terms),
        retrieved_at=evidence.retrieved_at,
    )


def build_intelligence(query: str, evidences: list[WebEvidence]) -> ProcurementIntelligenceResponse:
    """Cluster a set of stored evidences into analyst-grade intelligence.

    Items are grouped into the seven investigation clusters and, within each,
    ranked by confidence (strongest evidence first) so an analyst reads primary
    before weak. Inadmissible pages are silently dropped.
    """
    by_cluster: dict[str, list[ProcurementIntelligenceItem]] = defaultdict(list)
    total = 0
    for evidence in evidences:
        item = build_intelligence_item(evidence)
        if item is None:
            continue
        by_cluster[item.cluster].append(item)
        total += 1

    clusters: list[EvidenceCluster] = []
    for name in CLUSTERS:
        items = by_cluster.get(name, [])
        if not items:
            continue
        items.sort(key=lambda i: i.confidence, reverse=True)
        clusters.append(
            EvidenceCluster(
                cluster=name,
                label=_CLUSTER_LABELS[name],
                count=len(items),
                items=items,
            )
        )

    # Clusters ordered by total evidential weight so the most-substantiated
    # bucket leads the briefing.
    clusters.sort(key=lambda c: sum(i.confidence for i in c.items), reverse=True)
    return ProcurementIntelligenceResponse(query=query, total_items=total, clusters=clusters)
