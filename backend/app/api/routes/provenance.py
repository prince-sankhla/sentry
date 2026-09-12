from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.provenance.engine import CHAIN, build_demo_case, verify_case

router = APIRouter(prefix="/api/provenance", tags=["provenance"])


class VerifyRequest(BaseModel):
    case_id: str = "case"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    expected_steps: list[str] = Field(default_factory=lambda: list(CHAIN))
    allowed_signers: list[str] = Field(default_factory=lambda: ["pipeline", "builder", "release"])
    expected_products: dict[str, str] = Field(default_factory=dict)
    signature_scheme: str = "hmac-sha256"
    public_keys: dict[str, str] = Field(default_factory=dict)


@router.get("/contract")
def contract() -> dict[str, Any]:
    return {
        "statement": "CY-03 Software Supply-Chain Provenance Verification",
        "chain": CHAIN,
        "failure_families": [
            "missing_step",
            "hash_mismatch",
            "unauthorized_signer",
            "unexpected_product",
            "wrong_order",
        ],
        "safe_execution": "Artifacts are treated as text/hashes only; the verifier never executes generated artifacts.",
    }


@router.get("/demo")
def demo(mutation: str | None = None) -> dict[str, Any]:
    allowed = {None, "missing_step", "hash_mismatch", "unauthorized_signer", "unexpected_product", "wrong_order"}
    if mutation not in allowed:
        raise HTTPException(400, "Unsupported mutation")
    case = build_demo_case(mutation=mutation)
    return {"case": case, "verification": verify_case(case)}


@router.post("/verify")
def verify(request: VerifyRequest) -> dict[str, Any]:
    case = request.model_dump()
    result = verify_case(case)
    return {"case": case, "verification": result}


@router.get("/benchmark")
def benchmark() -> dict[str, Any]:
    mutations = [None, "missing_step", "hash_mismatch", "unauthorized_signer", "unexpected_product", "wrong_order"]
    rows = []
    for mutation in mutations:
        case = build_demo_case(case_id=f"benchmark-{mutation or 'clean'}", mutation=mutation)
        result = verify_case(case)
        rows.append({"case_id": case["case_id"], "mutation": mutation or "clean", "verdict": result["verdict"], "primary_violation": result["primary_violation"], "top_step": result["suspicious_steps"][0] if result["suspicious_steps"] else None})
    return {"cases": rows, "total": len(rows), "failure_families_covered": len(mutations) - 1}
