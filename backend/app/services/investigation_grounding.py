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


@dataclass(frozen=True)
class GroundingVerdict:
    """Result of verifying a generated summary against its evidence context."""

    grounded: bool
    ungrounded_numbers: list[str] = field(default_factory=list)
    reason: str = ""


def verify_summary(summary: str, context: str) -> GroundingVerdict:
    """Verify that ``summary`` introduces no quantity absent from ``context``.

    Returns a :class:`GroundingVerdict`. ``grounded`` is ``True`` when every
    numeric claim in the summary is traceable to the evidence context (or is a
    ubiquitous 0/1). Any other number makes the summary ungrounded and the caller
    should discard it in favour of the deterministic composer.
    """
    if not summary.strip():
        return GroundingVerdict(False, [], "empty summary")

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
    return GroundingVerdict(grounded=True, reason="all quantities trace to evidence")
