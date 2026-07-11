"""Print every procurement ingestion report as JSON.

    python scripts/procurement_reports.py                # all reports
    python scripts/procurement_reports.py --quality      # data-quality only
    python scripts/procurement_reports.py --coverage     # connector coverage/health
    python scripts/procurement_reports.py --dimensions   # multi-dimensional coverage
    python scripts/procurement_reports.py --statistics   # import statistics
    python scripts/procurement_reports.py --integrity    # evidence integrity
    python scripts/procurement_reports.py --connectors   # connector validation/health

Flags combine. Every number is read live from the ingestion database — nothing
is fabricated.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

import app.models  # noqa: E402,F401  (import-order side effect: resolves the model cycle)
from app.db.session import SessionLocal  # noqa: E402
from app.services.connector_validation import build_connector_health_report  # noqa: E402
from app.services.coverage_engine import build_coverage_engine_report  # noqa: E402
from app.services.coverage_report import build_coverage_report  # noqa: E402
from app.services.data_quality import build_data_quality_report  # noqa: E402
from app.services.evidence_integrity import build_evidence_integrity_report  # noqa: E402
from app.services.import_statistics import build_import_statistics  # noqa: E402
from app.services.procurement_platform.health import build_connector_dashboard  # noqa: E402
from app.services.procurement_platform.validators import run_validation  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Procurement ingestion reports (all deterministic).")
    parser.add_argument("--quality", action="store_true", help="Data-quality report.")
    parser.add_argument("--coverage", action="store_true", help="Connector coverage / health report.")
    parser.add_argument("--dimensions", action="store_true", help="Multi-dimensional coverage report.")
    parser.add_argument("--statistics", action="store_true", help="Import statistics report.")
    parser.add_argument("--integrity", action="store_true", help="Evidence integrity report.")
    parser.add_argument("--connectors", action="store_true", help="Connector validation report.")
    parser.add_argument("--dashboard", action="store_true", help="Connector health dashboard.")
    parser.add_argument("--validate", action="store_true", help="Run the validation harness.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = any(
        [args.quality, args.coverage, args.dimensions, args.statistics, args.integrity,
         args.connectors, args.dashboard, args.validate]
    )
    all_reports = not selected
    output: dict[str, object] = {}
    with SessionLocal() as session:
        if all_reports or args.statistics:
            output["statistics"] = build_import_statistics(session).model_dump()
        if all_reports or args.quality:
            output["data_quality"] = build_data_quality_report(session).model_dump()
        if all_reports or args.dimensions:
            output["coverage_dimensions"] = build_coverage_engine_report(session).model_dump()
        if all_reports or args.coverage:
            output["coverage"] = build_coverage_report(session).model_dump()
        if all_reports or args.integrity:
            output["evidence_integrity"] = build_evidence_integrity_report(session).model_dump()
        if all_reports or args.connectors:
            output["connector_health"] = build_connector_health_report(session).model_dump()
        if all_reports or args.dashboard:
            output["connector_dashboard"] = build_connector_dashboard(session).model_dump()
        if all_reports or args.validate:
            result = run_validation(session)
            output["validation"] = {"summary": result.summary, "checks": [vars(c) for c in result.checks]}
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
