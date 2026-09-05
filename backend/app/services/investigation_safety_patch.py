"""Runtime guardrails for evidence-safe investigation outputs.

The shipped legacy indicator builder still contains historical winner-count
proxies. This module applies the repository's current data-integrity policy at
application startup so winner-only award records never become bidder evidence,
and high-value awards are not mislabeled as direct awards without an evidenced
procurement method.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services import investigation_indicators, risk_engine

_APPLIED = False
_ORIGINAL_BUILD: Callable[..., list[Any]] | None = None
_ORIGINAL_ASSESS: Callable[..., Any] | None = None


def _sanitize(indicators: list[Any]) -> list[Any]:
    cleaned: list[Any] = []
    for indicator in indicators:
        indicator_type = getattr(indicator, "type", "")
        # Award records identify winners, not how many bids were received.
        # Without an explicit recorded_bidders field, the single-bidder proxy is
        # an unsupported competition conclusion and must not reach findings/risk.
        if indicator_type == "single_bidder":
            continue

        # A single recorded awardee is not evidence of a direct award. Keep the
        # high-value observation, but downgrade it to a generic high-value award
        # review lead until procurement-method/direct-award evidence exists.
        if indicator_type == "high_value_direct_award":
            cleaned.append(
                indicator.model_copy(
                    update={
                        "type": "high_value",
                        "severity": "medium",
                        "title": "High-Value Award",
                        "score": 60,
                        "confidence": min(float(getattr(indicator, "confidence", 0.6)), 0.6),
                        "summary": _high_value_summary(indicator),
                        "reason": _high_value_reason(indicator),
                        "evidence": [
                            text for text in getattr(indicator, "evidence", [])
                            if not str(text).casefold().startswith("recorded suppliers:")
                        ],
                    }
                )
            )
            continue

        cleaned.append(indicator)
    return cleaned


def _high_value_summary(indicator: Any) -> str:
    summary = str(getattr(indicator, "summary", "")).strip()
    # Preserve tender reference/value while removing the unsupported competition claim.
    marker = " was awarded to a single supplier."
    if marker in summary:
        return summary.replace(marker, " is a high-value procurement award.")
    return summary or "High-value procurement award requires additional review."


def _high_value_reason(indicator: Any) -> str:
    reason = str(getattr(indicator, "reason", "")).strip()
    marker = ", awarded to a single supplier ("
    start = reason.find(marker)
    if start >= 0:
        prefix = reason[:start]
        return prefix + ". The available award record does not establish the procurement method or level of competition."
    return reason or "The tender is in the high-value oversight band; procurement method and competition evidence require verification."


def apply_safety_patch() -> None:
    """Patch indicator/risk entry points once, before request handling begins."""
    global _APPLIED, _ORIGINAL_BUILD, _ORIGINAL_ASSESS
    if _APPLIED:
        return

    _ORIGINAL_BUILD = investigation_indicators.build_indicators

    def build_safe(pkg: Any) -> list[Any]:
        assert _ORIGINAL_BUILD is not None
        return _sanitize(_ORIGINAL_BUILD(pkg))

    investigation_indicators.build_indicators = build_safe
    # risk_engine imported the function directly, so patch its local alias too.
    risk_engine.build_indicators = build_safe

    _ORIGINAL_ASSESS = risk_engine.assess_risk_v2

    def assess_safe(pkg: Any, *args: Any, **kwargs: Any) -> Any:
        pkg.indicators = build_safe(pkg)
        assert _ORIGINAL_ASSESS is not None
        return _ORIGINAL_ASSESS(pkg, *args, **kwargs)

    risk_engine.assess_risk_v2 = assess_safe
    _APPLIED = True
