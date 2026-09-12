"""Deterministic CY-03 provenance verifier/localizer.

The benchmark contract is deliberately text/hash based: no generated artifact is
executed. Verification is therefore pure, deterministic, and safe to run on
untrusted cases.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass, asdict
from typing import Any

CHAIN = ["fetch", "deps", "compile", "test", "package", "scan", "sign", "publish"]
FAILURE_FAMILIES = {
    "missing_step": "Missing required step",
    "hash_mismatch": "Unexpected product hash",
    "unauthorized_signer": "Unauthorized signer",
    "unexpected_product": "Unexpected product",
    "wrong_order": "Adjacent steps in wrong order",
}


@dataclass
class Step:
    id: str
    name: str
    input_hash: str | None
    product: str
    product_hash: str
    signer_id: str | None = None
    signature: str | None = None
    signature_scheme: str = "hmac-sha256"


@dataclass
class Violation:
    family: str
    step_id: str
    invariant: str
    evidence: dict[str, Any]
    score: float


@dataclass
class Verification:
    case_id: str
    verdict: str
    suspicious_steps: list[dict[str, Any]]
    primary_violation: dict[str, Any] | None
    step_results: list[dict[str, Any]]
    violations: list[dict[str, Any]]
    explanation: str


def artifact_hash(case_id: str, step: str) -> str:
    return hashlib.sha256(f"artifact:20260911:{case_id}:{step}".encode()).hexdigest()


def signing_key(signer_id: str) -> bytes:
    return hashlib.sha256(f"key:20260911:{signer_id}".encode()).digest()


def sign_hmac(case_id: str, step: Step) -> str:
    message = f"{case_id}:{step.id}:{step.product_hash}".encode()
    return hmac.new(signing_key(step.signer_id or ""), message, hashlib.sha256).hexdigest()


def _verify_ed25519(public_key_b64: str, signature_b64: str, message: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        key.verify(base64.b64decode(signature_b64), message)
        return True
    except Exception:
        return False


def _normalise_steps(raw: list[dict[str, Any]]) -> list[Step]:
    return [Step(
        id=str(s.get("id", "")),
        name=str(s.get("name", "")),
        input_hash=s.get("input_hash"),
        product=str(s.get("product", "")),
        product_hash=str(s.get("product_hash", "")),
        signer_id=s.get("signer_id"),
        signature=s.get("signature"),
        signature_scheme=str(s.get("signature_scheme", "hmac-sha256")),
    ) for s in raw]


def build_demo_case(case_id: str = "demo-clean", mutation: str | None = None) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for i, name in enumerate(CHAIN):
        product = "source-bundle" if name == "fetch" else f"artifact-{name}"
        product_hash = artifact_hash(case_id, name)
        signer = "builder" if name in {"compile", "package", "sign"} else "pipeline"
        step = Step(f"s{i+1}", name, steps[-1]["product_hash"] if steps else None, product, product_hash, signer)
        step.signature = sign_hmac(case_id, step)
        steps.append(asdict(step))

    case = {
        "case_id": case_id,
        "expected_steps": CHAIN,
        "steps": steps,
        "allowed_signers": {"pipeline", "builder", "release"},
        "expected_products": {name: ("source-bundle" if name == "fetch" else f"artifact-{name}") for name in CHAIN},
        "signature_scheme": "hmac-sha256",
    }
    if mutation == "missing_step":
        case["steps"].pop(3)
    elif mutation == "hash_mismatch":
        case["steps"][3]["product_hash"] = "0" * 64
    elif mutation == "unauthorized_signer":
        case["steps"][6]["signer_id"] = "attacker"
        case["steps"][6]["signature"] = sign_hmac(case_id, Step(**case["steps"][6]))
    elif mutation == "unexpected_product":
        case["steps"][4]["product"] = "artifact-evil"
    elif mutation == "wrong_order":
        case["steps"][2], case["steps"][3] = case["steps"][3], case["steps"][2]
    return case


def verify_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id", "unknown"))
    expected = list(case.get("expected_steps") or CHAIN)
    allowed_signers = set(case.get("allowed_signers") or {"pipeline", "builder", "release"})
    expected_products = dict(case.get("expected_products") or {})
    steps = _normalise_steps(case.get("steps") or [])
    violations: list[Violation] = []
    step_results: list[dict[str, Any]] = []

    actual_names = [s.name for s in steps]
    # Missing step and wrong-order checks are independent so a malformed chain is
    # still fully explainable rather than failing at the first error.
    if actual_names != expected:
        missing = [n for n in expected if n not in actual_names]
        if missing:
            idx = expected.index(missing[0])
            near = steps[min(idx, len(steps)-1)].id if steps else "chain"
            violations.append(Violation("missing_step", near, "All 8 required steps must be present in canonical order", {"missing_step": missing[0]}, .95))
        for i in range(min(len(actual_names), len(expected)) - 1):
            if actual_names[i] != expected[i] or actual_names[i+1] != expected[i+1]:
                if i + 1 < len(actual_names) and set(actual_names[i:i+2]) == set(expected[i:i+2]) and actual_names[i:i+2] != expected[i:i+2]:
                    violations.append(Violation("wrong_order", steps[i].id, "Adjacent provenance steps must follow the declared chain order", {"expected": expected[i:i+2], "observed": actual_names[i:i+2]}, .90))
                    break

    for i, step in enumerate(steps):
        reasons: list[str] = []
        expected_hash = artifact_hash(case_id, step.name)
        if step.product_hash != expected_hash:
            reasons.append("hash_mismatch")
            violations.append(Violation("hash_mismatch", step.id, "Product hash must equal the deterministic expected artifact hash", {"expected_hash": expected_hash, "observed_hash": step.product_hash}, .92))
        if step.name in expected_products and step.product != expected_products[step.name]:
            reasons.append("unexpected_product")
            violations.append(Violation("unexpected_product", step.id, "Each step must emit its expected product", {"expected_product": expected_products[step.name], "observed_product": step.product}, .88))
        if step.signer_id not in allowed_signers:
            reasons.append("unauthorized_signer")
            violations.append(Violation("unauthorized_signer", step.id, "Signer must belong to the authorized signer set", {"signer_id": step.signer_id, "allowed_signers": sorted(allowed_signers)}, .94))
        if step.signature:
            message = f"{case_id}:{step.id}:{step.product_hash}".encode()
            valid = False
            if step.signature_scheme == "ed25519":
                keys = case.get("public_keys") or {}
                key = keys.get(step.signer_id or "")
                valid = bool(key) and _verify_ed25519(key, step.signature, message)
            else:
                valid = hmac.compare_digest(step.signature, sign_hmac(case_id, step))
            if not valid:
                reasons.append("signature_invalid")
                violations.append(Violation("unauthorized_signer", step.id, "Signature must authenticate the declared signer and product hash", {"signature_valid": False}, .94))
        else:
            reasons.append("signature_missing")
            violations.append(Violation("unauthorized_signer", step.id, "Each signed provenance assertion must carry an authentic signature", {"signature_present": False}, .94))

        step_results.append({"step_id": step.id, "name": step.name, "status": "fail" if reasons else "pass", "reasons": reasons})

    # Rank by strongest local evidence; ties are deterministic by chain position.
    scores: dict[str, float] = {s.id: 0.0 for s in steps}
    for v in violations:
        scores[v.step_id] = max(scores.get(v.step_id, 0.0), v.score)
    ranked = sorted((s for s in steps if scores.get(s.id, 0) > 0), key=lambda s: (-scores[s.id], s.name))
    suspicious = [{"step_id": s.id, "step": s.name, "score": round(scores[s.id], 4)} for s in ranked]
    primary = None
    if violations:
        primary_v = max(violations, key=lambda v: (v.score, -expected.index(v.evidence.get("expected_step", v.family)) if v.evidence.get("expected_step") in expected else 0))
        primary = {"family": primary_v.family, "invariant": primary_v.invariant, "step_id": primary_v.step_id, "evidence": primary_v.evidence}
    verdict = "FAIL" if violations else "PASS"
    if primary:
        explanation = f"{verdict}: top suspicious step {primary['step_id']} violates {primary['family']} — {primary['invariant']}."
    else:
        explanation = "PASS: all required provenance invariants, artifact hashes, products, ordering, and signatures verified."
    return asdict(Verification(case_id, verdict, suspicious, primary, step_results, [asdict(v) for v in violations], explanation))
