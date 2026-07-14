import sys
sys.path.insert(0, ".")
from datetime import datetime, timezone, date
from decimal import Decimal
from app.schemas.investigation_executor import (
    InvestigationAwardResult, InvestigationDocumentResult, InvestigationPackage,
    InvestigationProcurementRecord, InvestigationSourceMetadata, InvestigationTenderResult)
from app.schemas.investigation_planner import InvestigationPlan
from app.services.investigation_executor import _build_evidence, _build_entities
from app.services.investigation_indicators import build_indicators
from app.services.investigation_reasoning import build_reasoning
from app.services.risk_engine import assess_risk_v2
from app.services.investigation_packet import build_packet_document, render_packet_html

def meta(rid, src="cppp", url=None):
    return InvestigationSourceMetadata(source_name=src, source_record_id=rid,
        source_url=url or f"https://eprocure.gov.in/tender/{rid}", retrieved_at=datetime(2026,7,10,tzinfo=timezone.utc))

def rec(ref, buyer, suppliers, value, pub, close, aw, docs=True):
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(reference_number=ref, title=f"Supply of radar subsystems ({ref})",
            description="Procurement of radar subsystems and integration services.",
            procuring_entity=buyer, published_date=pub, closing_date=close,
            estimated_value=Decimal(value), currency="INR", metadata=meta(ref)),
        awards=[InvestigationAwardResult(tender_reference_number=ref, company_name=s,
            company_registration_number="L32309KA1954GOI000787", award_date=aw, award_value=Decimal(value),
            currency="INR", metadata=meta(f"{ref}:{s}")) for s in suppliers],
        documents=[InvestigationDocumentResult(title=f"Award notice {ref}", url=f"https://eprocure.gov.in/doc/{ref}.pdf",
            document_type="award_notice", metadata=meta("d"+ref))] if docs else [])

recs = [
    rec("BEL/2026/RADAR/040", "Bharat Electronics Limited || Bangalore Complex",
        ["Bharat Electronics Limited"], "1760000000", date(2026,1,15), date(2026,1,29), date(2026,2,10)),
    rec("BEL/2026/RADAR/041", "Bharat Electronics Limited || Bangalore Complex",
        ["Bharat Electronics Limited"], "480000000", date(2026,2,1), date(2026,2,15), date(2026,2,20)),
    rec("BEL/2026/COMP/012", "Bharat Electronics Limited || Bangalore Complex",
        ["Precision Components Pvt Ltd"], "92000000", date(2026,2,5), date(2026,2,26), date(2026,3,2)),
]
plan = InvestigationPlan(query="Bharat Electronics Limited", investigation_type="supplier",
    confidence=0.83, connectors=["cppp","gem"], modules=["retrieval","risk"], steps=[])
pkg = InvestigationPackage(plan=plan, records=recs)
pkg.evidence = _build_evidence(pkg); pkg.entities = _build_entities(pkg)
pkg.indicators = build_indicators(pkg); pkg.risk_assessment_v2 = assess_risk_v2(pkg)
reasoning = build_reasoning(pkg, "Bharat Electronics Limited")
doc = build_packet_document(pkg, reasoning, subject="Bharat Electronics Limited",
    generated_at=datetime(2026,7,11,tzinfo=timezone.utc))
html = render_packet_html(doc)
open("packet_current.html","w",encoding="utf-8").write(html)
print("WROTE", len(html), "bytes")
print("risk:", doc.risk_level, doc.risk_score, "| conf:", doc.confidence_pct, "| vlevel:", doc.verification_level)
print("typologies:", [(t.name,t.severity,t.kind) for t in doc.typologies])
print("exec_summary_len:", len(doc.ai_summary), "| provenance:", doc.ai_summary_provenance[:60])
print("missing_evidence:", doc.missing_evidence)
print("methodology_items:", len(doc.methodology))
