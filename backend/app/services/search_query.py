"""Shared full-text search query construction for procurement retrieval.

Centralises the ranked, fuzzy, synonym-expanded search used by both the
investigation record source and the HTTP search/tender routes so every surface
retrieves the same way:

* PostgreSQL full-text search (``search_vector`` tsvector) for ranked matches.
* ``pg_trgm`` similarity as a typo-tolerant fallback and secondary signal.
* Domain synonym expansion (Indian procurement vocabulary) so "road" also finds
  "highway"/"street", "medical" finds "hospital"/"health", etc.
* Indian-first ordering applied on top of relevance everywhere.

The helpers return SQLAlchemy expressions; callers own the final SELECT so
result shaping stays with each route.
"""

from __future__ import annotations

import re

from sqlalchemy import Float, and_, case, cast, func, literal, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.connectors.common.source_priority import _SOURCE_RANK, _UNKNOWN_RANK
from app.models import Award, Company, Tender

# Domain synonym groups — procurement vocabulary tuned for Indian tenders.
# Any query token that hits a group is expanded to the whole group so recall is
# not lost to wording differences (e.g. "highway" vs "road").
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"road", "roads", "highway", "highways", "street", "carriageway", "pavement"}),
    frozenset({"bridge", "bridges", "flyover", "overbridge", "rob", "culvert"}),
    frozenset({"hospital", "hospitals", "medical", "health", "healthcare", "clinic", "dispensary"}),
    frozenset({"medicine", "medicines", "drug", "drugs", "pharmaceutical", "pharma"}),
    frozenset({"school", "schools", "education", "educational", "college", "classroom"}),
    frozenset({"water", "sewer", "sewerage", "sanitation", "drainage", "pipeline", "pipe"}),
    frozenset({"electric", "electrical", "electricity", "power", "transformer", "substation"}),
    frozenset({"solar", "photovoltaic", "pv", "renewable"}),
    frozenset({"software", "application", "system", "portal", "digital", "it"}),
    frozenset({"computer", "hardware", "laptop", "server", "networking"}),
    frozenset({"construction", "civil", "building", "infrastructure", "works"}),
    frozenset({"railway", "railways", "rail", "train", "locomotive", "coach"}),
    frozenset({"supply", "supplies", "procurement", "purchase", "goods", "material"}),
    frozenset({"consultancy", "consultant", "consulting", "advisory"}),
    frozenset({"maintenance", "repair", "upkeep", "servicing"}),
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def expand_terms(query: str) -> list[str]:
    """Return the distinct search terms for a query, including domain synonyms."""
    tokens = [t for t in _TOKEN_RE.findall(query.casefold()) if len(t) > 1]
    if not tokens:
        return []
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            terms.append(token)
        for group in _SYNONYM_GROUPS:
            if token in group:
                for syn in sorted(group):
                    if syn not in seen:
                        seen.add(syn)
                        terms.append(syn)
    return terms


def tsquery(query: str):
    """Build a websearch tsquery OR-combined with synonym terms.

    Uses ``websearch_to_tsquery`` for the raw query (handles phrases/quotes) and
    ORs in the synonym-expanded lexemes so recall covers domain wording.
    """
    terms = expand_terms(query)
    base = func.websearch_to_tsquery("english", query)
    if not terms:
        return base
    synonym_expr = func.to_tsquery("english", " | ".join(terms))
    return base.op("||")(synonym_expr)


def source_rank_ordering():
    """SQL CASE mapping ``Tender.source_name`` to its Indian-first rank."""
    from sqlalchemy import case

    return case(
        {name: rank for name, rank in _SOURCE_RANK.items()},
        value=Tender.source_name,
        else_=_UNKNOWN_RANK,
    )


def relevance_score(query: str) -> ColumnElement:
    """Full-text rank + trigram similarity as a single relevance score."""
    ts = func.ts_rank(Tender.search_vector, tsquery(query))
    trg = func.similarity(Tender.title, literal(query.strip()))
    return (cast(ts, Float) * 4.0 + cast(trg, Float)).label("relevance")


def matches(query: str, *, min_similarity: float = 0.15) -> ColumnElement:
    """Boolean predicate: FTS match OR fuzzy trigram OR company-name match.

    Combines three recall paths so a record is found whether the query matches
    the tender text, a fuzzy/typo variant of the title/buyer, or an awarded
    company name — while staying index-backed (GIN fts + trigram).
    """
    q = query.strip()
    like = f"%{q}%"
    company_tender_ids = (
        select(Award.tender_id).join(Company, Award.company_id == Company.id).where(Company.name.ilike(like))
    )
    return or_(
        Tender.search_vector.op("@@")(tsquery(q)),
        Tender.title.op("%")(q),
        Tender.procuring_entity.op("%")(q),
        Tender.title.ilike(like),
        Tender.procuring_entity.ilike(like),
        Tender.reference_number.ilike(like),
        Tender.id.in_(company_tender_ids),
    )


# --------------------------------------------------------------------------- precision

# Words too generic to identify an entity — a query reduced to only these would
# match half the table, so entity precision retrieval ignores them.
_ENTITY_STOPWORDS: frozenset[str] = frozenset({
    "ltd", "limited", "pvt", "private", "company", "co", "corporation", "corp",
    "inc", "llp", "plc", "india", "the", "and", "of", "for", "projects", "project",
})


def _entity_terms(query: str) -> list[str]:
    """Identifying tokens of an entity query (stopwords stripped, length>2)."""
    tokens = [t for t in _TOKEN_RE.findall(query.casefold()) if len(t) > 2 and t not in _ENTITY_STOPWORDS]
    return tokens or [t for t in _TOKEN_RE.findall(query.casefold()) if len(t) > 1]


def _entity_field_match(text: str) -> ColumnElement:
    """A record references ``text`` in a supplier / buyer / title / reference field."""
    like = f"%{text}%"
    company_tender_ids = (
        select(Award.tender_id).join(Company, Award.company_id == Company.id).where(Company.name.ilike(like))
    )
    return or_(
        Tender.id.in_(company_tender_ids),    # awarded supplier is the entity
        Tender.procuring_entity.ilike(like),  # entity is the buyer
        Tender.title.ilike(like),             # tender names the entity
        Tender.reference_number.ilike(like),  # reference names the entity
    )


def entity_matches(query: str, *, aliases: list[str] | None = None) -> ColumnElement:
    """Precision predicate: a record must *directly reference* the entity.

    Unlike :func:`matches`, this deliberately does NOT use synonym-expanded
    full-text search — that is what pulls unrelated procurements (a "road"
    synonym dragging in every highway tender). A record qualifies only when the
    entity name, a known alias, or all of its identifying tokens appear in an
    awarded company, the tender title, the buyer, or the reference.

    Balances precision and recall:
      * full-name / alias reference (either phrasing), OR
      * every identifying token present across the entity fields (so "Tata
        Projects" matches a "Tata Projects Limited" supplier without matching an
        unrelated tender that merely shares one common word).

    ``aliases`` lets the resolved canonical entity contribute its known aliases
    so recall is preserved for genuine variants without opening the door to
    topical/synonym drift.
    """
    q = query.strip()
    names = [q, *[a.strip() for a in (aliases or []) if a and a.strip()]]

    # Full-name / alias direct references (each phrasing as a whole). We do NOT
    # add a trigram fuzzy buyer guard here: for multi-word names it drifts to
    # unrelated buyers that merely share a common word (e.g. "Delhi University" ~
    # "University of Calcutta" on the shared "university"). Precision comes from
    # the direct name match plus the all-identifying-tokens conjunction below.
    name_clauses: list[ColumnElement] = [_entity_field_match(name) for name in names if name]

    # Every identifying token present somewhere in the entity fields. Tokens come
    # from the query AND each alias, so an alias's distinctive token also counts.
    token_sources = [q, *[a for a in (aliases or []) if a]]
    tokens: list[str] = []
    seen: set[str] = set()
    for source in token_sources:
        for token in _entity_terms(source):
            if token not in seen:
                seen.add(token)
                tokens.append(token)

    token_requirements = [_entity_field_match(token) for token in tokens]

    direct = or_(*name_clauses) if name_clauses else None
    all_tokens = and_(*token_requirements) if token_requirements else None
    if direct is not None and all_tokens is not None:
        return or_(direct, all_tokens)
    return direct if direct is not None else (all_tokens if all_tokens is not None else matches(q))


def entity_relevance_score(query: str, *, aliases: list[str] | None = None) -> ColumnElement:
    """Precision relevance: exact supplier/buyer/title reference ranks highest.

    Builds an explainable additive score so the strongest entity match sorts
    first: awarded-supplier match > buyer match > title match > fuzzy title.
    """
    from sqlalchemy import Integer

    q = query.strip()
    like = f"%{q}%"
    company_tender_ids = (
        select(Award.tender_id).join(Company, Award.company_id == Company.id).where(Company.name.ilike(like))
    )
    supplier_hit = case((Tender.id.in_(company_tender_ids), 100), else_=0)
    buyer_hit = case((Tender.procuring_entity.ilike(like), 60), else_=0)
    title_hit = case((Tender.title.ilike(like), 40), else_=0)
    ref_hit = case((Tender.reference_number.ilike(like), 50), else_=0)
    trg = func.similarity(Tender.title, q)
    return (
        cast(supplier_hit, Integer)
        + cast(buyer_hit, Integer)
        + cast(title_hit, Integer)
        + cast(ref_hit, Integer)
        + cast(trg * 20.0, Float)
    ).label("entity_relevance")
