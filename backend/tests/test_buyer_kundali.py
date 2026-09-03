from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.buyer_kundali import (
    _award_estimate_distribution,
    _submission_window,
    _tender_distribution,
    _value_benchmark,
)


def tender(**overrides):
    data = {
        "id": uuid4(),
        "procuring_entity": "Buyer A",
        "published_date": date(2026, 1, 1),
        "closing_date": date(2026, 1, 8),
        "estimated_value": Decimal("100"),
        "currency": "INR",
        "category": "Roads",
        "geography": "Jaipur",
        "procurement_method": "Open",
        "awards": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def award(amount: str, tender_obj):
    return SimpleNamespace(award_value=Decimal(amount), tender=tender_obj)


def test_value_benchmark_is_contextual_and_ordered():
    result = _value_benchmark([Decimal("100"), Decimal("200"), Decimal("300"), Decimal("400")], "INR")
    assert result.sample_size == 4
    assert result.minimum == Decimal("100")
    assert result.p25 == Decimal("175")
    assert result.median == Decimal("250")
    assert result.p75 == Decimal("325")
    assert result.maximum == Decimal("400")
    assert result.currency == "INR"


def test_submission_window_preserves_unknown_dates():
    result = _submission_window([
        tender(published_date=date(2026, 1, 1), closing_date=date(2026, 1, 8)),
        tender(published_date=date(2026, 1, 1), closing_date=date(2026, 1, 15)),
        tender(published_date=None, closing_date=date(2026, 1, 15)),
    ])
    assert result.sample_size == 2
    assert result.minimum_days == 7
    assert result.maximum_days == 14
    assert result.unknown_count == 1


def test_distribution_exposes_unknown_dimension_as_context():
    rows = _tender_distribution([
        tender(category="Roads"),
        tender(category="Roads"),
        tender(category=None),
    ], "category", "Category")
    assert rows[0].name == "Roads"
    assert rows[0].count == 2
    assert rows[0].share == Decimal("2") / Decimal("3")
    assert rows[-1].name == "Unknown / not stored"
    assert rows[-1].count == 1


def test_award_estimate_ratio_is_available_only_when_both_values_exist():
    first = tender(estimated_value=Decimal("100"), awards=[award("120", None)])
    first.awards[0].tender = first
    second = tender(estimated_value=None, awards=[award("80", None)])
    second.awards[0].tender = second
    result = _award_estimate_distribution([first, second])
    assert result is not None
    assert result.count == 1
    assert result.value == Decimal("1.2")
