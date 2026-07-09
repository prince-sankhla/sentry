"""Source authority classification for procurement web intelligence.

The Procurement Intelligence Engine must return *only* investigation-relevant
evidence from authoritative sources — never generic web results. This module is
the single gatekeeper that decides whether a URL is admissible and how much
evidential weight it carries.

Design
------
* **Allow-list first.** A URL is admitted only when its host matches a known
  authoritative source *class* (government/tender portals, oversight bodies,
  courts, regulators, company-filing registries, official PDFs, procurement
  news desks). Everything else is rejected by default — the safe direction for
  a "reject generic web" mandate.
* **Explicit reject-list.** Shopping, blogs, marketing/SEO, entertainment,
  generic encyclopaedia and social domains are rejected even if a keyword
  matched, so a marketing page that mentions "tender" cannot slip through.
* **Deterministic + explainable.** Classification is pure string/host logic with
  a stated ``reason`` — auditable, never model-driven, so it cannot hallucinate
  an authority it does not have.

The classifier returns an :class:`SourceClassification`; the search route uses
``admissible`` as a hard gate and ``authority`` to weight confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

# --------------------------------------------------------------------------- tiers

# Authority tier -> base weight (0-100). Mirrors the Evidence Engine's philosophy
# that official Indian procurement/oversight sources are primary evidence.
AUTHORITY_WEIGHT: dict[str, int] = {
    "government_portal": 42,   # CPPP, GeM, state eProc, ministries, .gov.in / .nic.in
    "oversight_body": 40,      # CAG, CVC, CCI, RTI portals
    "judicial": 38,            # court judgments, arbitration, tribunals
    "regulator": 36,           # SEBI, MCA / company filings, RBI
    "official_pdf": 34,        # any .pdf served from an admissible host
    "procurement_news": 22,    # recognised procurement / tender news desks
    "unknown": 0,              # not admissible
}

SourceType = str  # one of AUTHORITY_WEIGHT keys


@dataclass(frozen=True)
class SourceClassification:
    """Verdict for a single URL: is it admissible, and how authoritative."""

    admissible: bool
    source_type: SourceType
    authority: int
    label: str
    reason: str


# --------------------------------------------------------------------------- host rules

# Exact or suffix host matches for authoritative Indian government + oversight
# sources. Suffix match: a rule "gov.in" matches "eprocure.gov.in".
_GOVERNMENT_SUFFIXES: tuple[str, ...] = (
    "gov.in",
    "nic.in",
    "gembuyer.in",
    "gem.gov.in",
    "eprocure.gov.in",
    "cppp.gov.in",
    "gov",           # generic government TLD-style (e.g. *.gov) — still official
)

# Oversight / audit / anti-corruption / competition bodies.
_OVERSIGHT_HOSTS: tuple[str, ...] = (
    "cag.gov.in",        # Comptroller and Auditor General
    "cvc.gov.in",        # Central Vigilance Commission
    "cci.gov.in",        # Competition Commission of India
    "rti.gov.in",
    "rtionline.gov.in",
)

# Judicial: court judgments, arbitration, tribunals.
_JUDICIAL_HOSTS: tuple[str, ...] = (
    "sci.gov.in",           # Supreme Court of India
    "main.sci.gov.in",
    "judgments.ecourts.gov.in",
    "ecourts.gov.in",
    "indiankanoon.org",     # widely-cited Indian judgment repository
    "livelaw.in",           # law reporting — judgment texts (procurement/arbitration)
    "barandbench.com",
    "nclt.gov.in",          # National Company Law Tribunal
    "nclat.nic.in",
)

# Regulators + statutory company-filing / disclosure registries.
_REGULATOR_HOSTS: tuple[str, ...] = (
    "sebi.gov.in",
    "bseindia.com",         # exchange disclosures / annual reports
    "nseindia.com",
    "mca.gov.in",           # Ministry of Corporate Affairs filings
    "rbi.org.in",
)

# Recognised procurement / tender news desks. Kept deliberately narrow: only
# outlets whose beat is public procurement, so this does not become a generic
# news allow-list.
_PROCUREMENT_NEWS_HOSTS: tuple[str, ...] = (
    "biddetail.com",
    "tendersontime.com",
    "tenderdetail.com",
    "globaltenders.com",
    "pib.gov.in",           # Press Information Bureau — official govt press releases
)

# Hard reject: even if procurement keywords appear, these are never evidence.
_REJECT_SUFFIXES: tuple[str, ...] = (
    "wikipedia.org",
    "amazon.in",
    "amazon.com",
    "flipkart.com",
    "indiamart.com",
    "justdial.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "medium.com",
    "blogspot.com",
    "wordpress.com",
    "quora.com",
    "glassdoor.com",
    "naukri.com",
    "tripadvisor.com",
    "pinterest.com",
)

# Path/host fragments that mark marketing, SEO, shopping, careers, entertainment,
# admissions, contact/about and college pages even on otherwise-allowed hosts.
# These are never procurement intelligence, so they are rejected regardless of
# host authority (a gov/edu contact or admissions page is still not evidence).
_REJECT_FRAGMENTS: tuple[str, ...] = (
    "/blog/",
    "/careers",
    "/jobs",
    "/shop",
    "/product/",
    "/cart",
    "/pricing",
    "/reviews",
    "/entertainment",
    "/sports",
    "/lifestyle",
    "utm_source",
    # admissions / college / contact / marketing pages
    "/admission",
    "/admissions",
    "/apply",
    "/prospectus",
    "/course",
    "/courses",
    "/programme",
    "/programs",
    "/faculty",
    "/alumni",
    "/student",
    "/campus",
    "/syllabus",
    "/contact",
    "/contact-us",
    "/about-us",
    "/aboutus",
    "/enquiry",
    "/gallery",
    "/events",
    "/newsletter",
)


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower().split(":")[0].lstrip(".")


def _host_matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in suffixes)


def classify_source(url: str, *, title: str | None = None) -> SourceClassification:
    """Classify a URL's source authority and admissibility.

    Rejection wins over admission: a reject-listed host or a marketing/SEO/shopping
    path fragment is never admissible, even if it also looks governmental.
    """
    host = _host(url)
    if not host:
        return SourceClassification(False, "unknown", 0, "", "no host in URL")

    lowered = url.lower()

    # 1. Hard reject-list — junk domains and marketing/shopping/SEO paths.
    if _host_matches(host, _REJECT_SUFFIXES):
        return SourceClassification(False, "unknown", 0, host, f"rejected domain: {host}")
    if any(fragment in lowered for fragment in _REJECT_FRAGMENTS):
        return SourceClassification(False, "unknown", 0, host, "marketing/SEO/shopping path")

    is_pdf = lowered.split("?", 1)[0].endswith(".pdf")

    # 2. Authoritative source classes (most specific first).
    if _host_matches(host, _OVERSIGHT_HOSTS):
        return _admit("oversight_body", host, "audit/oversight body", is_pdf)
    if _host_matches(host, _JUDICIAL_HOSTS):
        return _admit("judicial", host, "court/arbitration record", is_pdf)
    if _host_matches(host, _REGULATOR_HOSTS):
        return _admit("regulator", host, "regulator/company filing", is_pdf)
    if _host_matches(host, _GOVERNMENT_SUFFIXES):
        return _admit("government_portal", host, "government/tender portal", is_pdf)
    if _host_matches(host, _PROCUREMENT_NEWS_HOSTS):
        return _admit("procurement_news", host, "procurement news", is_pdf)

    # 3. An official-looking PDF on an unknown host is admitted only weakly if its
    #    host still resembles an institutional domain; otherwise rejected.
    if is_pdf and _looks_institutional(host):
        return _admit("official_pdf", host, "official PDF", True)

    return SourceClassification(False, "unknown", 0, host, "not an allow-listed procurement source")


def _admit(source_type: SourceType, host: str, label: str, is_pdf: bool) -> SourceClassification:
    authority = AUTHORITY_WEIGHT[source_type]
    reason = f"{label} ({host})"
    if is_pdf and source_type != "official_pdf":
        # An official PDF from an already-authoritative host is the strongest
        # form of that source — a primary document, not a rendered web page.
        authority = min(100, authority + 6)
        reason += " · official PDF"
    return SourceClassification(True, source_type, authority, host, reason)


def _looks_institutional(host: str) -> bool:
    """Heuristic for an institutional host (govt/edu/org) hosting a PDF."""
    return host.endswith((".org", ".edu", ".ac.in", ".res.in", ".int"))


# Strong procurement-intelligence signal terms across every ALLOWED evidence
# category (procurement, contracts, audit, litigation, regulatory, compliance).
# An evidence item must contain at least one to be returned — this is the content
# relevance check that rejects admissions / college / contact / marketing pages
# even on allow-listed government or educational hosts, while still admitting the
# full set of procurement-intelligence categories the mission enumerates.
_PROCUREMENT_SIGNALS: tuple[str, ...] = (
    # procurement / contracts
    "tender", "e-tender", "etender", "notice inviting", "nit ", "rfp",
    "request for proposal", "eoi", "expression of interest", "bid", "bidder",
    "bidding", "award", "awarded", "letter of award", "loa ", "contract",
    "work order", "purchase order", "procurement", "e-procurement", "gem",
    "cppp", "empanel", "corrigendum", "bill of quantities", "boq", "emd",
    "earnest money", "tender fee", "quotation", "supply of", "procuring entity",
    "lowest bidder", "l1 ",
    # audit / vigilance
    "audit", "cag", "vigilance", "cvc", "irregularit", "misappropriation",
    # compliance / debarment
    "debar", "debarment", "blacklist", "black list", "banned", "show cause",
    # litigation / arbitration (court judgments)
    "judgment", "judgement", "writ", "petition", "petitioner", "respondent",
    "arbitration", "arbitral", "tribunal", "high court", "supreme court",
    # regulatory / financial
    "sebi", "competition commission", "disclosure", "regulation 30", "insider",
    "annual report", "balance sheet", "financial statement",
    # official
    "gazette", "notification", "press information bureau", "press release",
)

# Terms that mark admissions / college / contact / marketing content. When these
# dominate and no procurement signal is present the page is rejected outright.
_NON_PROCUREMENT_SIGNALS: tuple[str, ...] = (
    "admission", "prospectus", "syllabus", "undergraduate", "postgraduate",
    "scholarship", "hostel", "faculty", "alumni", "enrol", "semester",
    "apply now", "contact us", "about us", "our team", "privacy policy",
    "add to cart", "buy now", "best price", "book now", "showtimes",
)


def is_procurement_relevant(title: str | None, url: str, text: str | None) -> bool:
    """Content relevance gate: is this page actually procurement intelligence?

    Every evidence item must pass this before being returned. A page qualifies
    only when it carries at least one strong procurement signal; an admissions /
    college / contact / marketing page with none is rejected even if it sits on
    an allow-listed government or educational host.
    """
    haystack = " ".join(part for part in [title or "", url, (text or "")[:16000]] if part).casefold()
    if not any(sig in haystack for sig in _PROCUREMENT_SIGNALS):
        return False
    # A page swamped by admissions/marketing terms with only a stray procurement
    # word is still rejected when the non-procurement signal clearly dominates.
    non_proc = sum(1 for sig in _NON_PROCUREMENT_SIGNALS if sig in haystack)
    proc = sum(1 for sig in _PROCUREMENT_SIGNALS if sig in haystack)
    return proc >= non_proc or proc >= 2
