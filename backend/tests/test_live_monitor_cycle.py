from types import SimpleNamespace

from scripts.live_monitor_cycle import discover_links, flagged_references


def test_cppp_discovery_rejects_non_official_hosts() -> None:
    html = '''
    <a href="https://www.eprocure.gov.in/eprocure/app?service=direct&component=view&page=FrontEndTenderDetails&id=2026_X_1_1">official</a>
    <a href="https://example.com/eprocure/app?service=direct&component=view&page=FrontEndTenderDetails&id=2026_X_2_2">external</a>
    '''
    links = discover_links(html, source="cppp")
    assert len(links) == 1
    assert links[0].startswith("https://www.eprocure.gov.in/")


def test_flagged_references_keeps_only_indicator_tenders() -> None:
    assessment = SimpleNamespace(
        indicators=[
            SimpleNamespace(related_tenders=["T-001", "T-003"]),
        ]
    )
    package = SimpleNamespace(risk_assessment_v2=assessment)
    assert flagged_references(package) == {"T-001", "T-003"}


def test_no_indicators_persists_nothing() -> None:
    assessment = SimpleNamespace(indicators=[])
    package = SimpleNamespace(risk_assessment_v2=assessment)
    assert flagged_references(package) == set()
