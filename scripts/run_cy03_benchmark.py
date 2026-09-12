"""Generate machine-readable CY-03 benchmark predictions.

Usage from repository root: python scripts/run_cy03_benchmark.py > cy03_predictions.json
No artifact is executed; only deterministic text/hash cases are verified.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.provenance.engine import build_demo_case, verify_case


def main() -> None:
    mutations = [None, "missing_step", "hash_mismatch", "unauthorized_signer", "unexpected_product", "wrong_order"]
    predictions = []
    for mutation in mutations:
        case = build_demo_case(f"benchmark-{mutation or 'clean'}", mutation)
        result = verify_case(case)
        predictions.append({
            "case_id": case["case_id"],
            "verdict": result["verdict"],
            "suspicious_step_ids": [x["step_id"] for x in result["suspicious_steps"]],
            "primary_violation": result["primary_violation"],
        })
    print(json.dumps(predictions, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
