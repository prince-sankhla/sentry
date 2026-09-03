"""COMP-001 Competition Anomaly Detector.

CRITICAL DATA LIMITATION:
-------------------------
The current repository does NOT have individual bid records (Bid model).
Only Award records (winners) exist.

Award count ≠ Bidder count:
- Award count = number of winners (typically 1)
- Bidder count = total participants (may be 5+ bidders, 1 winner)

Therefore, COMP-001 cannot currently detect true competition anomalies.

This module returns INSUFFICIENT_DATA and documents what P1 Bid ingestion would unlock.

DO NOT interpret this detector's output as detecting collusion or fraud.
It flags data gaps, not wrongdoing.
"""

from __future__ import annotations

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_risk import RiskIndicatorV2


def detect_comp001_competition_anomaly(
    pkg: InvestigationPackage,
    db,
) -> list[RiskIndicatorV2]:
    """Detect competition anomalies using available data.

    CURRENT LIMITATION:
    - No Bid model exists
    - Only Award (winner) count available
    - Award count is NOT bidder count
    - Returns empty list (cannot assess without bid data)

    Args:
        pkg: Investigation package with tender/award records
        db: Database session for benchmark queries

    Returns:
        Empty list (COMP-001 requires Bid model, not yet implemented)
    """
    # HONEST IMPLEMENTATION: Return empty list until Bid model exists
    # Do not fabricate competition signals from award data
    return []


def detect_comp001_with_bid_data(
    pkg: InvestigationPackage,
    db,
) -> list[RiskIndicatorV2]:
    """FUTURE: Competition anomaly detector when Bid model exists.

    This function documents the CORRECT implementation once P1 Bid
    ingestion is complete.

    Algorithm:
    1. For each tender, count responsive bids (bidder_count)
    2. Build benchmark: get_benchmark(db, dimensions, metric="bidder_count")
       - Dimensions: buyer, category, procurement_method, geography, value_band
       - Metric: bidder_count (NOT award_count)
    3. Compare observed vs benchmark:
       - If bidder_count < benchmark.p25: potential anomaly
       - If bidder_count < 2 AND benchmark.median >= 5: strong anomaly
       - Deviation = (observed - median) / IQR
    4. Context checks:
       - Emergency procurement? (legitimate low competition)
       - Specialized/niche procurement? (thin market acceptable)
       - Framework agreement? (pre-qualified suppliers)
    5. Confidence:
       - High: Large benchmark sample, all dimensions match
       - Medium: Moderate sample, some dimensions missing
       - Low: Small sample, many dimensions missing
    6. Return RiskIndicatorV2:
       - severity: "low", "medium", "high", or "critical"
       - evidence_status: "verified", "probable", "unknown"
       - confidence: 0.0-1.0
       - reason: Contextual explanation
       - required_evidence: List what's needed for verification
       - supporting_records: Tender references
       - context_notes: Benchmark details

    DO NOT implement this function yet.
    Wait for P1 Bid model.
    """
    raise NotImplementedError(
        "Bid model does not exist. "
        "Implement P1 Bid ingestion before calling this function."
    )
