"""Evidence typing + clustering for procurement web intelligence.

Every admitted page is classified along two axes:

* **evidence_type** — the specific nature of the record (award_notice,
  tender_notice, debarment, blacklisting, audit_finding, court_judgment,
  arbitration, regulatory_filing, annual_report, procurement_news, …). This is
  the noun an analyst cites.
* **cluster** — one of the seven investigation buckets the intelligence is
  grouped under: ``contracts``, ``litigation``, ``audit``, ``compliance``,
  ``financial``, ``news``, ``government``.

Both are derived deterministically from the page's source class, URL, title and
text via scored keyword signals, so the classification is explainable and cannot
invent a category the evidence does not support. When no signal is strong enough
the type is ``procurement_record`` in the ``government`` cluster (the neutral
default for an admitted government source).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.webintel.source_authority import SourceClassification

# Canonical cluster names — the seven required investigation buckets.
CLUSTERS: tuple[str, ...] = (
    "contracts",
    "litigation",
    "audit",
    "compliance",
    "financial",
    "news",
    "government",
)


@dataclass(frozen=True)
class EvidenceTypeSignal:
    evidence_type: str
    cluster: str
    keywords: tuple[str, ...]
    weight: int = 1


# Ordered by specificity: red-flag evidence (debarment/blacklisting/audit) is
# listed before generic contract/tender types so it wins on ties. Each keyword
# is matched case-folded against the title+url+text haystack.
_SIGNALS: tuple[EvidenceTypeSignal, ...] = (
    # --- litigation ---
    EvidenceTypeSignal("court_judgment", "litigation",
        ("judgment", "judgement", "writ petition", "vs ", " v. ", "hon'ble", "high court", "supreme court", "bench"), 3),
    EvidenceTypeSignal("arbitration", "litigation",
        ("arbitration", "arbitral", "arbitrator", "tribunal award", "section 34", "conciliation"), 3),
    EvidenceTypeSignal("litigation", "litigation",
        ("litigation", "petitioner", "respondent", "cause list", "appeal no", "case no"), 2),
    # --- audit ---
    EvidenceTypeSignal("audit_finding", "audit",
        ("audit report", "cag report", "audit observation", "audit para", "performance audit", "compliance audit"), 3),
    EvidenceTypeSignal("vigilance_finding", "audit",
        ("vigilance", "cvc", "preliminary enquiry", "irregularit"), 2),
    # --- compliance (debarment / blacklisting / integrity) ---
    EvidenceTypeSignal("debarment", "compliance",
        ("debar", "debarment", "debarred", "banned firm", "banning"), 3),
    EvidenceTypeSignal("blacklisting", "compliance",
        ("blacklist", "black list", "black-list", "put on hold", "suspension of business dealings"), 3),
    EvidenceTypeSignal("integrity_notice", "compliance",
        ("integrity pact", "conflict of interest", "code of integrity", "penalty imposed", "show cause"), 2),
    # --- regulatory / financial ---
    EvidenceTypeSignal("regulatory_filing", "financial",
        ("sebi", "disclosure", "regulation 30", "insider trading", "listing obligation"), 3),
    EvidenceTypeSignal("annual_report", "financial",
        ("annual report", "balance sheet", "profit and loss", "director's report", "financial statement"), 2),
    EvidenceTypeSignal("company_filing", "financial",
        ("mca", "roc filing", "shareholding", "board resolution", "annual return"), 2),
    # --- contracts (awards / tenders / contracts) ---
    EvidenceTypeSignal("award_notice", "contracts",
        ("award of contract", "award notice", "letter of award", "loa", "contract awarded", "awarded to", "notification of award"), 3),
    EvidenceTypeSignal("contract_announcement", "contracts",
        ("work order", "contract agreement", "purchase order", "contract signed", "contract value"), 2),
    EvidenceTypeSignal("tender_notice", "contracts",
        ("tender notice", "notice inviting tender", "nit", "request for proposal", "rfp", "bid invitation", "e-tender", "corrigendum"), 2),
    # --- news / press ---
    EvidenceTypeSignal("press_release", "news",
        ("press release", "press information bureau", "pib", "official statement"), 2),
    EvidenceTypeSignal("procurement_news", "news",
        ("scam", "probe", "cbi", "ed ", "enforcement directorate", "fir ", "chargesheet", "corruption"), 2),
)

# Source-type -> default (evidence_type, cluster) when no keyword signal fires.
_SOURCE_DEFAULTS: dict[str, tuple[str, str]] = {
    "oversight_body": ("audit_finding", "audit"),
    "judicial": ("court_judgment", "litigation"),
    "regulator": ("regulatory_filing", "financial"),
    "government_portal": ("procurement_record", "government"),
    "official_pdf": ("official_document", "government"),
    "procurement_news": ("procurement_news", "news"),
}


@dataclass(frozen=True)
class EvidenceClassification:
    evidence_type: str
    cluster: str
    matched_terms: tuple[str, ...]
    score: int


def classify_evidence(
    source: SourceClassification,
    *,
    title: str | None,
    url: str,
    text: str,
) -> EvidenceClassification:
    """Assign an evidence type + cluster from source class and page signals."""
    haystack = " ".join(part for part in [title or "", url, (text or "")[:12000]] if part).casefold()

    best: EvidenceTypeSignal | None = None
    best_score = 0
    best_terms: list[str] = []
    for signal in _SIGNALS:
        terms = [kw for kw in signal.keywords if kw in haystack]
        if not terms:
            continue
        score = len(terms) * signal.weight
        if score > best_score:
            best, best_score, best_terms = signal, score, terms

    if best is not None:
        return EvidenceClassification(best.evidence_type, best.cluster, tuple(best_terms), best_score)

    default_type, default_cluster = _SOURCE_DEFAULTS.get(
        source.source_type, ("procurement_record", "government")
    )
    return EvidenceClassification(default_type, default_cluster, (), 0)
