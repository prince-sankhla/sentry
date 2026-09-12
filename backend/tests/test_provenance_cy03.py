from app.provenance.engine import CHAIN, artifact_hash, build_demo_case, verify_case


def test_clean_case_passes() -> None:
    result = verify_case(build_demo_case("test-clean"))
    assert result["verdict"] == "PASS"
    assert result["violations"] == []
    assert [x["name"] for x in result["step_results"]] == CHAIN


def test_all_required_mutations_are_detected() -> None:
    expected = {
        "missing_step": "missing_step",
        "hash_mismatch": "hash_mismatch",
        "unauthorized_signer": "unauthorized_signer",
        "unexpected_product": "unexpected_product",
        "wrong_order": "wrong_order",
    }
    for mutation, family in expected.items():
        result = verify_case(build_demo_case(f"test-{mutation}", mutation))
        assert result["verdict"] == "FAIL"
        assert any(v["family"] == family for v in result["violations"])
        assert result["suspicious_steps"]


def test_artifact_hash_is_deterministic() -> None:
    assert artifact_hash("case-a", "compile") == artifact_hash("case-a", "compile")
    assert artifact_hash("case-a", "compile") != artifact_hash("case-b", "compile")
