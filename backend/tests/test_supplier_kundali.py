from decimal import Decimal
from types import SimpleNamespace

from app.services.supplier_kundali import _concentration, _quantile, _value_benchmark


def _award(buyer: str | None, category: str | None, value: str) -> SimpleNamespace:
    return SimpleNamespace(
        award_value=Decimal(value),
        tender=SimpleNamespace(procuring_entity=buyer, category=category),
    )


def test_supplier_concentration_preserves_unknown_population() -> None:
    awards = [
        _award("Buyer A", "Works", "100"),
        _award("Buyer A", "Works", "200"),
        _award(None, "Goods", "300"),
    ]

    rows = _concentration(awards, lambda award: award.tender.procuring_entity, "Buyer")

    assert [(row.name, row.count, row.share) for row in rows] == [
        ("Buyer A", 2, Decimal("0.6666666666666666666666666667")),
        ("Unknown / not stored", 1, Decimal("0.3333333333333333333333333333")),
    ]
    assert rows[0].value == Decimal("300")
    assert rows[0].population_count == 3


def test_supplier_value_benchmark_is_decimal_safe() -> None:
    benchmark = _value_benchmark(
        [Decimal("100"), Decimal("200"), Decimal("300"), Decimal("400")],
        "INR",
    )

    assert benchmark.sample_size == 4
    assert benchmark.minimum == Decimal("100")
    assert benchmark.p25 == Decimal("175.00")
    assert benchmark.median == Decimal("250")
    assert benchmark.p75 == Decimal("325.00")
    assert benchmark.maximum == Decimal("400")
    assert benchmark.currency == "INR"


def test_quantile_handles_single_value() -> None:
    assert _quantile([Decimal("42")], 0.75) == Decimal("42")
