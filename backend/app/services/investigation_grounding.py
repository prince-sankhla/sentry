"""Grounding guard — post-generation verification for LLM-phrased narratives.

The reasoning layer lets a live model *phrase* an executive summary, but the
model is never allowed to introduce facts. This module is the enforcement point
for that contract: it checks a generated summary against the exact evidence
context the model was given and rejects any output that asserts a number,
monetary value, or percentage the evidence does not contain.

Design principles
-----------------
* **Deterministic.** No model is involved in verification — the guard is a pure
  function of (summary, context), so its verdict is itself auditable.
* **Fail safe, not loud.** When the guard trips, the caller falls back to the
  deterministic composer, which is grounded by construction. A false positive
  therefore only costs us the model's phrasing, never correctness — the right
  trade-off under a "never hallucinate" mandate.
* **Numbers first.** In a 2-4 sentence briefing the highest-risk, most-verifiable
  fabrication is a quantity (₹ value, share %, record/award count). Every numeric
  token in the summary must be traceable to the evidence context. Prose that
  carries no numbers cannot smuggle a quantitative claim past the guard.

The guard is intentionally strict on quantities and silent on wording: it never
rewrites the model's text, it only accepts or rejects it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Digit runs with optional grouping separators / decimals: "5", "1,200", "3.5",
# and Indian grouping like "5,00,000". Percentages and money reduce to the bare
# number ("60%" -> 60, "₹5,00,000" -> 500000), which is what we verify.
_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Small English number-words a model may spell out instead of using digits. We
# convert these to their digit form so "seven tenders" is verified the same way
# as "7 tenders" — a spelled number is still a quantitative claim.
_WORD_NUMBERS: dict[str, str] = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
}

# Numbers so generic that their appearance in prose is never a factual claim
# about the evidence (ordinals/articles like "a single bidder", "the first").
# Kept tiny on purpose — anything larger must trace to the context.
_UBIQUITOUS: frozenset[str] = frozenset({"0", "1"})

# Organizational designators that mark a capitalized phrase as a NAMED ENTITY
# (a company or government body) rather than ordinary prose. A summary asserting
# "awarded to X Ltd" or "the Y Corporation" is making an entity claim that must
# trace to the evidence context — inventing a supplier/buyer is the highest-value
# non-numeric fabrication a judge probes. We anchor on designators (not every
# capitalized word) to keep the guard high-precision: sentence-initial words and
# generic prose like "Risk is HIGH" never carry these, so they are never flagged.
_ENTITY_DESIGNATORS: frozenset[str] = frozenset({
    "ltd", "limited", "pvt", "private", "llp", "inc", "corp", "corporation",
    "company", "co", "industries", "enterprises", "enterprise", "infrastructure",
    "infra", "constructions", "construction", "builders", "engineers",
    "engineering", "technologies", "solutions", "services", "systems", "nigam",
    "authority", "board", "ministry", "department", "municipal", "municipality",
    "corporation", "council", "commission", "agency", "trust", "foundation",
    "gmbh", "plc", "sa", "ag", "bv", "nv",
})

# Words we ignore when checking whether an entity phrase traces to the context —
# risk/section vocabulary that is not itself an evidentiary entity token.
_ENTITY_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "of", "and", "risk", "high", "medium", "low", "critical",
    "investigation", "tender", "award", "supplier", "buyer", "report", "analyst",
})


def _normalize_number(raw: str) -> str:
    """Canonicalize a numeric token for comparison.

    Strips grouping commas, drops a trailing decimal zero-fraction, and removes
    leading zeros so "05", "5", and "5.0" all compare equal to "5".
    """
    cleaned = raw.replace(",", "")
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    cleaned = cleaned.lstrip("0")
    return cleaned or "0"


def numeric_atoms(text: str) -> set[str]:
    """Every distinct quantity asserted by ``text``, normalized.

    Includes both digit numbers and spelled small numbers so the guard sees a
    quantity however the model chose to write it.
    """
    atoms = {_normalize_number(match) for match in _NUM_RE.findall(text)}
    lowered = text.casefold()
    for word, digit in _WORD_NUMBERS.items():
        if re.search(rf"\b{word}\b", lowered):
            atoms.add(digit)
    return atoms


def entity_atoms(text: str) -> set[str]:
    """Every distinct NAMED ENTITY phrase asserted by ``text``.

    A named entity is a run of capitalized tokens anchored by an organizational
    designator (``... Ltd``, ``... Corporation``, ``... Nigam``). We return the
    phrase casefolded so it can be checked against the evidence context. Prose
    without a designator yields nothing, so ordinary capitalized words (sentence
    starts, "HIGH", "Risk") never register as an entity claim.
    """
    entities: set[str] = set()
    # Grow contiguous capitalized runs; a run is a named entity when any token in
    # it is an organizational designator.
    words = re.findall(r"[A-Za-z&.\-]+", text)
    run: list[str] = []
    for word in words:
        is_cap = bool(word) and word[0].isupper()
        if is_cap:
            run.append(word)
            continue
        _flush_entity_run(run, entities)
        run = []
    _flush_entity_run(run, entities)
    return entities


def _flush_entity_run(run: list[str], out: set[str]) -> None:
    """If a capitalized run contains an org designator, record it as an entity."""
    if len(run) < 2:
        return
    lowered = [w.casefold().rstrip(".") for w in run]
    if any(tok in _ENTITY_DESIGNATORS for tok in lowered):
        out.add(" ".join(lowered))


def _entity_is_grounded(entity: str, context_lower: str) -> bool:
    """An entity phrase traces to context if the phrase appears verbatim, or all
    of its significant (non-stopword, non-designator) tokens appear in context."""
    if entity in context_lower:
        return True
    significant = [
        tok for tok in entity.split()
        if tok not in _ENTITY_STOPWORDS and tok not in _ENTITY_DESIGNATORS and len(tok) > 1
    ]
    if not significant:
        # Phrase was only designators/stopwords (e.g. "the Corporation") — too
        # generic to be a fabrication claim; do not flag.
        return True
    return all(tok in context_lower for tok in significant)


@dataclass(frozen=True)
class GroundingVerdict:
    """Result of verifying a generated summary against its evidence context."""

    grounded: bool
    ungrounded_numbers: list[str] = field(default_factory=list)
    ungrounded_entities: list[str] = field(default_factory=list)
    reason: str = ""


def verify_summary(summary: str, context: str) -> GroundingVerdict:
    """Verify that ``summary`` introduces no quantity absent from ``context``.

    Returns a :class:`GroundingVerdict`. ``grounded`` is ``True`` when every
    numeric claim in the summary is traceable to the evidence context (or is a
    ubiquitous 0/1). Any other number makes the summary ungrounded and the caller
    should discard it in favour of the deterministic composer.
    """
    if not summary.strip():
        return GroundingVerdict(False, [], [], "empty summary")

    context_numbers = numeric_atoms(context)
    summary_numbers = numeric_atoms(summary)
    ungrounded = sorted(
        n for n in summary_numbers if n not in context_numbers and n not in _UBIQUITOUS
    )
    if ungrounded:
        return GroundingVerdict(
            grounded=False,
            ungrounded_numbers=ungrounded,
            reason=(
                "summary asserts quantities absent from the evidence context: "
                + ", ".join(ungrounded)
            ),
        )

    # Entity guard: reject any NAMED organization the evidence context does not
    # contain. Numbers are the highest-value fabrication, but inventing a
    # supplier/buyer is the next — and prose-only fabrications would otherwise
    # slip past a numbers-only guard. Fail-safe: a false positive only costs the
    # model's phrasing (caller falls back to the grounded deterministic composer).
    context_lower = context.casefold()
    ungrounded_entities = sorted(
        e for e in entity_atoms(summary) if not _entity_is_grounded(e, context_lower)
    )
    if ungrounded_entities:
        return GroundingVerdict(
            grounded=False,
            ungrounded_entities=ungrounded_entities,
            reason=(
                "summary names entities absent from the evidence context: "
                + ", ".join(ungrounded_entities)
            ),
        )
    return GroundingVerdict(grounded=True, reason="all quantities and named entities trace to evidence")
