"""Pre-investigation canonical entity resolution.

An investigation must never run on ambiguous free text. Given a query like
"Tata", this service resolves it to the specific canonical companies it could
mean — "Tata Projects Ltd", "Tata Steel Ltd", "Tata Motors Ltd", … — ranked by
how strongly each matches, and flags when explicit selection is required so
unrelated companies are never merged into one investigation.

Ranking (spec-aligned, strongest first):
    1. exact          — the query is the company name
    2. registration   — the query is (or contains) a CIN / registration number
    3. alias          — the query matches a known alias / normalized form
    4. official_name  — the query is a token-complete prefix of the official name
    5. fuzzy          — high fuzzy similarity, still above threshold

Everything is derived from the real ``companies`` table and their procurement
activity, so a candidate's rank reflects genuine evidence, not guesswork.
"""

from __future__ import annotations

import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.entity_resolution.matcher import match_company
from app.entity_resolution.normalizer import company_tokens, normalize_company_name
from app.models import Award, Company, Tender
from app.schemas.entity_resolution import EntityCandidate, EntityResolutionResult

# A CIN / registration-looking token: long alphanumeric with digits (e.g. an
# Indian CIN "L28920MH1945PLC004520") — used to route to a registration match.
_REGISTRATION_RE = re.compile(r"\b[A-Z0-9]{6,}\b", re.IGNORECASE)

# Candidate ceilings so the endpoint stays fast and the UI list stays legible.
_SCAN_LIMIT = 400
_MAX_CANDIDATES = 8

# Score floors by match type (0-100). Distinct so ranking reflects match quality.
_MATCH_SCORE = {
    "exact": 100,
    "registration": 98,
    "alias": 88,
    "official_name": 80,
    "fuzzy": 60,
}

# Curated Indian government / PSU acronym → canonical name aliases. Many marquee
# entities are queried by acronym ("BHEL", "NHAI") but stored under their full
# name, so an acronym alone would otherwise resolve to nothing. Expanding the
# query to the canonical form (and matching either) is a canonical-entity
# coverage improvement, not a retrieval heuristic. Keys are compared casefolded.
_ACRONYM_ALIASES: dict[str, str] = {
    "bhel": "Bharat Heavy Electricals",
    "bel": "Bharat Electronics",
    "nhai": "National Highways Authority of India",
    "cpwd": "Central Public Works Department",
    "ntpc": "National Thermal Power Corporation",
    "ongc": "Oil and Natural Gas Corporation",
    "gail": "GAIL India",
    "sail": "Steel Authority of India",
    "drdo": "Defence Research and Development Organisation",
    "isro": "Indian Space Research Organisation",
    "dmrc": "Delhi Metro Rail Corporation",
    "irctc": "Indian Railway Catering and Tourism Corporation",
    "bsnl": "Bharat Sanchar Nigam",
    "hal": "Hindustan Aeronautics",
    "railtel": "RailTel Corporation of India",
    "nbcc": "NBCC India",
    "cppp": "Central Public Procurement Portal",
    "du": "Delhi University",
    "iit": "Indian Institute of Technology",
    "aiims": "All India Institute of Medical Sciences",
    "asi": "Archaeological Survey of India",
    "gem": "Government e Marketplace",
    "bdl": "Bharat Dynamics Limited",
    "cci": "Cement Corporation of India",
    "fci": "Food Corporation of India",
    "pgcil": "Power Grid Corporation of India",
    "nhpc": "NHPC",
    "hpcl": "Hindustan Petroleum Corporation",
    "bpcl": "Bharat Petroleum Corporation",
    "iocl": "Indian Oil Corporation",
    "cpwd": "Central Public Works Department",
    "mtnl": "Mahanagar Telephone Nigam",
    "cag": "Comptroller and Auditor General of India",
    "cvc": "Central Vigilance Commission",
}


def _query_forms(query: str) -> list[str]:
    """The query plus any curated canonical expansion (e.g. "BHEL" → full name)."""
    forms = [query]
    expansion = _ACRONYM_ALIASES.get(query.casefold().strip())
    if expansion and expansion.casefold() != query.casefold():
        forms.append(expansion)
    return forms


def resolve_entities(session: Session, query: str, *, limit: int = _MAX_CANDIDATES) -> EntityResolutionResult:
    """Resolve free text to ranked canonical entity candidates."""
    q = (query or "").strip()
    if not q:
        return EntityResolutionResult(
            query=query, resolved=False, requires_disambiguation=False,
            reason="empty query",
        )

    # Expand well-known acronyms to their canonical form so "BHEL"/"NHAI" resolve
    # even though the store holds the full name. We match on whichever form hits.
    forms = _query_forms(q)
    match_q = forms[-1]  # canonical expansion when present, else the raw query
    normalized_q = normalize_company_name(match_q)
    query_tokens = company_tokens(match_q)

    # Pull a bounded candidate pool across all query forms: name/registration
    # ILIKE plus any company sharing a token PREFIX, so "Tata" reaches every
    # Tata* entity and "BHEL" reaches "Bharat Heavy Electricals Limited".
    pool_clauses = []
    for form in forms:
        pool_clauses.append(Company.name.ilike(f"%{form}%"))
        pool_clauses.append(Company.registration_number.ilike(f"%{form}%"))
    pool_clauses += [Company.name.ilike(f"%{_token_prefix(tok)}%") for tok in list(query_tokens)[:6]]
    statement = select(Company).where(or_(*pool_clauses)).limit(_SCAN_LIMIT)
    companies = list(session.scalars(statement).unique())

    candidates: list[EntityCandidate] = []
    seen_keys: set[str] = set()
    for company in companies:
        scored = _score_candidate(match_q, normalized_q, query_tokens, company)
        if scored is None:
            continue
        candidates.append(scored)
        seen_keys.add(normalize_company_name(scored.canonical_name))

    # Canonical entities are not only suppliers: a procuring entity (government
    # buyer) is equally a valid investigation subject. "Delhi University" is a
    # buyer, never a row in ``companies`` — so also resolve against distinct
    # procuring entities, or queries for buyers would return zero candidates.
    for buyer in _buyer_candidates(session, match_q, normalized_q, query_tokens):
        key = normalize_company_name(buyer.canonical_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        candidates.append(buyer)

    if not candidates:
        return EntityResolutionResult(
            query=q, resolved=False, requires_disambiguation=False,
            reason="no canonical entity matched the query",
        )

    # Enrich with procurement activity (grounding) and rank.
    _attach_activity(session, candidates)
    candidates.sort(key=lambda c: (c.score, c.confidence, c.tender_count + c.award_count), reverse=True)
    candidates = candidates[:limit]

    decision = _decide(q, normalized_q, candidates)
    return decision


def _score_candidate(
    query: str, normalized_q: str, query_tokens: set[str], company: Company
) -> EntityCandidate | None:
    """Score one company against the query; None if it does not match at all."""
    name = company.name
    normalized_name = normalize_company_name(name)
    reg = company.registration_number

    match_type: str
    reason: str
    confidence: float

    # 1. exact (raw or normalized name equality)
    if query.casefold().strip() == name.casefold().strip() or (normalized_q and normalized_q == normalized_name):
        match_type, reason, confidence = "exact", f"query equals canonical name “{name}”", 1.0
    # 2. registration / CIN
    elif reg and _looks_like_registration(query) and query.replace(" ", "").casefold() in reg.casefold():
        match_type, reason, confidence = "registration", f"query matches registration/CIN {reg}", 0.99
    else:
        # Use the shared matcher for alias/fuzzy grounding.
        m = match_company(name, query, right_registration_number=None, left_registration_number=reg)
        name_tokens = company_tokens(name)
        # Prefix-aware coverage so plural/singular and partial names still match
        # ("tata project" covers "tata projects"; "tata" covers "tata steel").
        coverage = _query_token_coverage(query_tokens, name_tokens)
        if m.matched and m.reason in {"normalized_name", "exact_name"}:
            match_type, reason, confidence = "alias", f"normalized form matches “{name}”", max(m.confidence, 0.88)
        elif coverage >= 0.999:
            # Every query token appears in the official name (prefix-aware), e.g.
            # "tata projects" ⊆ "Tata Projects Ltd" or "tata project" → the same.
            match_type, reason, confidence = "official_name", f"query matches official name “{name}”", 0.82
        elif m.matched:
            match_type, reason, confidence = "fuzzy", f"fuzzy match to “{name}” ({m.reason})", max(m.confidence, 0.6)
        elif coverage >= 0.5 and m.confidence >= 0.82:
            # Near-miss: most query tokens covered AND high fuzzy similarity — an
            # inflected/typo variant of a real name rather than an unrelated one.
            match_type, reason, confidence = "fuzzy", f"fuzzy match to “{name}”", max(m.confidence, 0.6)
        else:
            return None

    score = _MATCH_SCORE[match_type]
    return EntityCandidate(
        entity_id=str(company.id),
        canonical_name=name,
        entity_type="company",
        registration_number=reg,
        aliases=[],
        match_type=match_type,
        match_reason=reason,
        matched_field="registration_number" if match_type == "registration" else "name",
        score=score,
        confidence=round(min(1.0, confidence), 2),
        sources=[company.source_name] if company.source_name else [],
    )


def _buyer_segments(procuring_entity: str) -> list[str]:
    """All distinct segments of a ``org||dept||sub`` buyer string (canonical first).

    Government buyers are stored pipe-delimited; the first segment is the
    canonical organisation and the remaining segments (departments, acronyms like
    "NHAI"/"CPWD") are legitimate aliases the query may name directly.
    """
    seen: list[str] = []
    for part in procuring_entity.split("||"):
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return seen


def _buyer_first_segment(procuring_entity: str) -> str:
    """Canonical buyer name = the first segment of a ``a||b||c`` buyer string."""
    return _buyer_segments(procuring_entity)[0] if _buyer_segments(procuring_entity) else ""


def _buyer_candidates(
    session: Session, query: str, normalized_q: str, query_tokens: set[str]
) -> list[EntityCandidate]:
    """Resolve the query against distinct procuring entities (government buyers).

    Buyers are stored as pipe-delimited ``organisation||dept||sub`` strings in
    ``tenders.procuring_entity``; the canonical name is the first segment and the
    other segments (e.g. the acronym "NHAI") are aliases. Each distinct buyer is
    scored against its canonical name AND its aliases, and its tender volume
    grounds the ranking.
    """
    like = f"%{query}%"
    token_clauses = [Tender.procuring_entity.ilike(f"%{_token_prefix(tok)}%") for tok in list(query_tokens)[:6]]
    rows = session.execute(
        select(Tender.procuring_entity, func.count(Tender.id))
        .where(Tender.procuring_entity.is_not(None))
        .where(or_(Tender.procuring_entity.ilike(like), *token_clauses))
        .group_by(Tender.procuring_entity)
        .limit(_SCAN_LIMIT)
    ).all()

    # Collapse sub-department variants to their canonical first segment, summing
    # tender counts and unioning aliases so "Delhi University||..." rolls up to
    # one "Delhi University" while "...||NHAI" keeps NHAI as a resolvable alias.
    by_canonical: dict[str, tuple[str, int, list[str]]] = {}
    for procuring_entity, count in rows:
        segments = _buyer_segments(procuring_entity)
        if not segments:
            continue
        canonical = segments[0]
        aliases = segments[1:]
        key = normalize_company_name(canonical)
        prev = by_canonical.get(key)
        merged_aliases = list(prev[2]) if prev else []
        for a in aliases:
            if a not in merged_aliases:
                merged_aliases.append(a)
        by_canonical[key] = (canonical, (prev[1] if prev else 0) + int(count), merged_aliases)

    candidates: list[EntityCandidate] = []
    for canonical, tender_count, aliases in by_canonical.values():
        scored = _score_buyer(query, normalized_q, query_tokens, canonical, aliases, tender_count)
        if scored is not None:
            candidates.append(scored)
    return candidates


def _score_buyer(
    query: str, normalized_q: str, query_tokens: set[str], name: str, aliases: list[str], tender_count: int
) -> EntityCandidate | None:
    """Score a government buyer against the query, matching name OR any alias.

    The best match across the canonical name and its aliases (departments,
    acronyms) wins, so "NHAI" resolves the "National Highways Authority of
    India||NHAI||…" buyer while the canonical name stays the full organisation.
    """
    best: tuple[str, str, float] | None = None  # (match_type, reason, confidence)
    for target in [name, *aliases]:
        normalized_target = normalize_company_name(target)
        if query.casefold().strip() == target.casefold().strip() or (normalized_q and normalized_q == normalized_target):
            cand = ("exact", f"query equals buyer “{name}”" if target == name else f"query equals buyer alias “{target}” ({name})", 1.0)
        else:
            m = match_company(target, query)
            coverage = _query_token_coverage(query_tokens, company_tokens(target))
            if m.matched and m.reason in {"normalized_name", "exact_name"}:
                cand = ("alias", f"normalized form matches buyer “{target}”", max(m.confidence, 0.88))
            elif coverage >= 0.999:
                label = name if target == name else f"{target}” (alias of “{name}”)"
                cand = ("official_name", f"query matches buyer “{label}", 0.82)
            elif m.matched:
                cand = ("fuzzy", f"fuzzy match to buyer “{target}” ({m.reason})", max(m.confidence, 0.6))
            elif coverage >= 0.5 and m.confidence >= 0.82:
                cand = ("fuzzy", f"fuzzy match to buyer “{target}”", max(m.confidence, 0.6))
            else:
                continue
        if best is None or _MATCH_SCORE[cand[0]] > _MATCH_SCORE[best[0]]:
            best = cand
    if best is None:
        return None
    match_type, reason, confidence = best
    normalized_name = normalize_company_name(name)

    return EntityCandidate(
        entity_id=f"buyer:{normalized_name}",
        canonical_name=name,
        entity_type="government_buyer",
        registration_number=None,
        aliases=aliases,
        match_type=match_type,
        match_reason=reason,
        matched_field="procuring_entity",
        score=_MATCH_SCORE[match_type],
        confidence=round(min(1.0, confidence), 2),
        tender_count=tender_count,
        sources=[],
    )


def _attach_activity(session: Session, candidates: list[EntityCandidate]) -> None:
    """Count tenders/awards per company candidate so ranking reflects activity.

    Only company candidates carry a real ``companies.id``; buyer candidates keep
    the tender volume already computed in :func:`_buyer_candidates`.
    """
    company_ids = [c.entity_id for c in candidates if c.entity_type == "company"]
    if not company_ids:
        return
    rows = session.execute(
        select(Award.company_id, func.count(Award.id), func.count(func.distinct(Award.tender_id)))
        .where(Award.company_id.in_(company_ids))
        .group_by(Award.company_id)
    ).all()
    by_id = {str(cid): (int(awards), int(tenders)) for cid, awards, tenders in rows}
    for c in candidates:
        if c.entity_type != "company":
            continue
        awards, tenders = by_id.get(c.entity_id, (0, 0))
        c.award_count = awards
        c.tender_count = tenders


def _decide(query: str, normalized_q: str, candidates: list[EntityCandidate]) -> EntityResolutionResult:
    """Decide whether the query resolves to one entity or needs selection."""
    top = candidates[0]

    # A single unambiguous exact/registration hit resolves immediately.
    unique_exact = [c for c in candidates if c.match_type in {"exact", "registration"}]
    if len(unique_exact) == 1 and (len(candidates) == 1 or candidates[1].score < top.score):
        return EntityResolutionResult(
            query=query, resolved=True, requires_disambiguation=False,
            candidates=candidates, selected_entity_id=unique_exact[0].entity_id,
            reason=f"unambiguous {unique_exact[0].match_type} match",
        )

    # One candidate clearly dominates (big score gap) — resolve to it but keep
    # the alternatives visible for transparency.
    if len(candidates) == 1:
        return EntityResolutionResult(
            query=query, resolved=True, requires_disambiguation=False,
            candidates=candidates, selected_entity_id=top.entity_id,
            reason="single candidate",
        )
    if top.score - candidates[1].score >= 20:
        return EntityResolutionResult(
            query=query, resolved=True, requires_disambiguation=False,
            candidates=candidates, selected_entity_id=top.entity_id,
            reason="dominant candidate",
        )

    # Multiple plausible entities — require explicit selection. Never merge them.
    return EntityResolutionResult(
        query=query, resolved=False, requires_disambiguation=True,
        candidates=candidates, selected_entity_id=None,
        reason=f"{len(candidates)} plausible entities — explicit selection required",
    )


def _token_prefix(token: str) -> str:
    """Truncate a token to a stable prefix so plural/singular forms co-match.

    A 6+ char token is clipped to its first 5 chars for the DB pool ILIKE (e.g.
    "projects" → "proje"), so both "project" and "projects" reach the same names.
    Short tokens are used whole to avoid over-broad matches.
    """
    return token[:5] if len(token) >= 6 else token


def _query_token_coverage(query_tokens: set[str], name_tokens: set[str]) -> float:
    """Fraction of query tokens covered by a name token (prefix-aware).

    A query token counts as covered when it equals, is a prefix of, or has as a
    prefix, some name token — so "project" covers "projects" and vice versa. This
    is what lets partial and inflected names ("Tata Project") resolve to the
    canonical entity ("Tata Projects Ltd") instead of returning zero candidates.
    """
    if not query_tokens:
        return 0.0
    covered = 0
    for qt in query_tokens:
        for nt in name_tokens:
            if qt == nt or (len(qt) >= 4 and (nt.startswith(qt) or qt.startswith(nt))):
                covered += 1
                break
    return covered / len(query_tokens)


def _looks_like_registration(text: str) -> bool:
    token = text.replace(" ", "")
    return bool(_REGISTRATION_RE.fullmatch(token)) and any(ch.isdigit() for ch in token)
