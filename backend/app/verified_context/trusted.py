"""Phase 2 — Trusted Context Retrieval.

When the local Verified Context Library has no matching card, this provider
retrieves procurement guidance from TRUSTED procurement authorities only and
returns it as a **Draft Context Card** — never saved permanently, never marked
verified, always carrying its source citations and verification questions.

Determinism and honesty come from the design:

  * ``TRUSTED_AUTHORITIES`` is a hard allowlist of procurement authorities
    (GFR / CVC / CAG / ministry manuals / OCP / World Bank / OECD / ADB).
    A source that is not in the allowlist cannot produce a card, ever.
  * ``_GUIDANCE_CORPUS`` is SENTRY's curated extract of guidance from those
    authorities — conservative summaries with the publishing authority and its
    official location preserved on every entry. The provider only *selects*
    from this corpus; it never composes new guidance, so retrieval is
    deterministic and nothing is invented.
  * Cards come back with ``status="draft"``: Phase 3's human verification is
    the only path into the permanent library.

The provider plugs into the Phase 1 ``ContextProvider`` interface unchanged;
the engine, schema, and store are untouched, and no investigation pipeline
calls this subsystem yet — existing behaviour is identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.verified_context.providers import ContextProvider, LocalStoreProvider
from app.verified_context.schema import (
    CONTEXT_UNAVAILABLE,
    ContextCard,
    ContextQuery,
    ContextResolution,
    ContextSource,
)

# ------------------------------------------------------------------ authorities

@dataclass(frozen=True)
class TrustedAuthority:
    """One procurement authority SENTRY is allowed to retrieve guidance from."""

    key: str
    publisher: str
    url: str                      # official site (site-level, stable)
    domains: tuple[str, ...]      # allowlist — retrieval outside these is forbidden


TRUSTED_AUTHORITIES: dict[str, TrustedAuthority] = {
    "gfr": TrustedAuthority(
        "gfr", "Ministry of Finance, Department of Expenditure (General Financial Rules)",
        "https://doe.gov.in", ("doe.gov.in",),
    ),
    "cvc": TrustedAuthority(
        "cvc", "Central Vigilance Commission", "https://cvc.gov.in", ("cvc.gov.in",),
    ),
    "cag": TrustedAuthority(
        "cag", "Comptroller and Auditor General of India", "https://cag.gov.in", ("cag.gov.in",),
    ),
    "ocp": TrustedAuthority(
        "ocp", "Open Contracting Partnership", "https://www.open-contracting.org",
        ("open-contracting.org", "standard.open-contracting.org"),
    ),
    "worldbank": TrustedAuthority(
        "worldbank", "World Bank Procurement Framework", "https://www.worldbank.org",
        ("worldbank.org",),
    ),
    "oecd": TrustedAuthority(
        "oecd", "OECD Public Procurement Guidance", "https://www.oecd.org", ("oecd.org",),
    ),
    "adb": TrustedAuthority(
        "adb", "Asian Development Bank Procurement", "https://www.adb.org", ("adb.org",),
    ),
}


def is_trusted_domain(url: str) -> bool:
    """True only when ``url`` belongs to an allowlisted authority domain."""
    host = url.split("//", 1)[-1].split("/", 1)[0].casefold()
    return any(
        host == domain or host.endswith("." + domain)
        for authority in TRUSTED_AUTHORITIES.values()
        for domain in authority.domains
    )


# ------------------------------------------------------------------ corpus

@dataclass(frozen=True)
class GuidanceEntry:
    """One curated extract of trusted procurement guidance."""

    entry_id: str
    authority_key: str            # must exist in TRUSTED_AUTHORITIES
    document: str                 # the guidance document this extract summarises
    guidance: str                 # conservative summary — selected, never composed
    indicators: tuple[str, ...]   # finding types this guidance can contextualise
    questions: tuple[str, ...] = field(default_factory=tuple)
    jurisdictions: tuple[str, ...] = field(default_factory=tuple)  # empty = general


_GUIDANCE_CORPUS: tuple[GuidanceEntry, ...] = (
    GuidanceEntry(
        "gfr-single-bid",
        "gfr",
        "Manual for Procurement of Goods (Ministry of Finance)",
        "Government procurement manuals recognise that a single responsive bid may be "
        "considered for acceptance when the tender was adequately publicised, sufficient "
        "bidding time was allowed, qualification criteria were not unduly restrictive and "
        "the price is reasonable — with reasons recorded in writing; otherwise re-tendering "
        "is the norm.",
        ("single_bidder",),
        (
            "Was the tender adequately publicised with sufficient bidding time?",
            "Is a written single-bid acceptance justification on file?",
            "Was price reasonableness analysed against the estimate?",
        ),
        ("IN",),
    ),
    GuidanceEntry(
        "gfr-emergency-direct",
        "gfr",
        "General Financial Rules 2017 (emergency / urgency provisions)",
        "GFR and ministry manuals permit procurement without open tender in situations of "
        "emergency or urgency, subject to recorded justification and sanction at the "
        "prescribed level of authority.",
        ("high_value_direct_award", "single_bidder"),
        (
            "Is a recorded emergency/urgency justification on file?",
            "Was sanction obtained at the level prescribed for this value?",
        ),
        ("IN",),
    ),
    GuidanceEntry(
        "cvc-splitting",
        "cvc",
        "CVC guidance on splitting of sanctions/works",
        "CVC guidance directs that a work must not be split into smaller works in order to "
        "avoid the sanction of a higher authority. Delivering one sanctioned programme as "
        "multiple lots remains permissible when the packaging decision is recorded and "
        "approval is taken at the level appropriate to the aggregate value.",
        ("contract_fragmentation",),
        (
            "Was administrative/financial sanction taken on the aggregate value?",
            "Is the lot-wise packaging decision recorded and justified?",
        ),
        ("IN",),
    ),
    GuidanceEntry(
        "gfr-year-end-rush",
        "gfr",
        "General Financial Rules 2017 (even phasing of expenditure)",
        "GFR requires expenditure to be phased evenly through the year and cautions against "
        "a rush of expenditure at the close of the financial year; year-end clustering of "
        "awards is a recognised phenomenon in audit, and the underlying approvals must "
        "still be in order.",
        ("award_clustering", "repeat_supplier"),
        (
            "Do sanction and approval dates precede the year-end window?",
            "Does the funding source lapse at financial year close?",
        ),
        ("IN",),
    ),
    GuidanceEntry(
        "ocp-repeat-winner",
        "ocp",
        "OCP red flags for integrity in public contracting",
        "Open Contracting Partnership guidance treats repeated awards to the same supplier "
        "as a signal that requires bid-participation context — how many bidders competed "
        "and how they were evaluated — rather than as evidence of collusion by itself.",
        ("repeat_supplier", "buyer_concentration", "supplier_concentration"),
        ("Do bid registers show how many bidders competed and lost?",),
    ),
    GuidanceEntry(
        "ocp-award-publication",
        "ocp",
        "Open Contracting Data Standard (award publication guidance)",
        "Open contracting guidance expects award information to be published within a "
        "defined period after the award decision; the absence of a published award for a "
        "recently closed tender is consistent with a normal in-progress lifecycle.",
        ("missing_award_data",),
        ("Has the award-publication window for this portal elapsed?",),
    ),
    GuidanceEntry(
        "gfr-bid-time",
        "gfr",
        "General Financial Rules 2017 (minimum bidding time)",
        "Government procurement rules prescribe minimum bid-submission periods for open "
        "tenders; compressed timelines are permissible only with recorded reasons or where "
        "a corrigendum legitimately reset the schedule.",
        ("suspicious_timing",),
        (
            "Do recorded reasons justify the compressed timeline?",
            "Did a corrigendum reset the schedule?",
        ),
        ("IN",),
    ),
    GuidanceEntry(
        "worldbank-cost-estimates",
        "worldbank",
        "World Bank Procurement Regulations (cost estimation)",
        "Multilateral procurement frameworks require cost estimates to rest on a documented "
        "methodology; a divergence between estimate and award value is examined against the "
        "estimate file rather than presumed improper.",
        ("abnormal_value", "high_value", "award_value_exceeds_tender"),
        ("Is the cost-estimate methodology documented in the estimate file?",),
    ),
)


# ------------------------------------------------------------------ provider

class TrustedRetrievalProvider(ContextProvider):
    """Phase 2 provider: trusted-source guidance → Draft Context Cards.

    Runs AFTER the local library (priority 10 > LocalStoreProvider's 0).
    Selects the corpus entries relevant to the queried finding, builds one
    Draft card per entry with citations and verification questions preserved,
    and returns them WITHOUT persisting anything — drafts exist only in the
    resolution, awaiting Phase 3 verification.
    """

    name = "trusted_retrieval"
    priority = 10

    def resolve(self, query: ContextQuery) -> ContextResolution:
        drafts = [
            self._draft_card(entry)
            for entry in _GUIDANCE_CORPUS
            if query.indicator_id in entry.indicators
            and _scope_ok(entry.jurisdictions, query.jurisdiction)
        ]
        if drafts:
            drafts.sort(key=lambda c: c.card_id)  # deterministic order
            return ContextResolution(
                available=True,
                cards=drafts,
                message="Draft context retrieved from trusted sources — requires verification before reuse.",
                provider=self.name,
            )
        return ContextResolution(available=False, message=CONTEXT_UNAVAILABLE, provider=self.name)

    def _draft_card(self, entry: GuidanceEntry) -> ContextCard:
        authority = TRUSTED_AUTHORITIES[entry.authority_key]
        return ContextCard(
            card_id=f"draft-{entry.entry_id}",
            title=entry.document,
            summary=entry.guidance,
            applies_to_indicators=list(entry.indicators),
            jurisdictions=list(entry.jurisdictions),
            verification_questions=list(entry.questions),
            sources=[ContextSource(title=entry.document, url=authority.url, publisher=authority.publisher)],
            status="draft",   # NEVER verified by retrieval alone
        )


def _scope_ok(declared: tuple[str, ...], requested: str) -> bool:
    return not declared or not requested or requested in declared


# ------------------------------------------------------------------ factory

def build_default_engine():
    """The Phase 2 workflow: local Verified Context Library first, trusted
    retrieval only when the library has nothing. Composition-only — the
    Phase 1 engine class is reused unchanged."""
    from app.verified_context.engine import VerifiedContextEngine

    return VerifiedContextEngine([LocalStoreProvider(), TrustedRetrievalProvider()])
