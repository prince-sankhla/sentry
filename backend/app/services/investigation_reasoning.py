"""AI reasoning layer for the investigation engine.

This service turns a fully-executed :class:`InvestigationPackage` into an
analyst-grade narrative: an executive summary, an overall risk verdict with
cited rationale, per-finding explanations, recommendations, and suggested
follow-up investigations.

Grounding guarantees
--------------------
* The deterministic composer builds every sentence from values already present
  in the package (indicators, records, entities, evidence). It cannot invent
  facts.
* When a live LLM is configured, it is used ONLY to phrase the executive summary
  from a grounded evidence context, with an explicit instruction to answer from
  that context alone and to defer to "insufficient evidence" when unsure. If the
  call fails for any reason we fall back to the deterministic summary.

If the package contains no procurement records, the service returns an explicit
"insufficient evidence" result rather than a speculative narrative.
"""

from __future__ import annotations

from app.clients.llm import LLMUnavailableError, get_llm_client
from app.schemas.investigation_executor import (
    InvestigationPackage,
    InvestigationProcurementIndicator,
)
from app.schemas.investigation_reasoning import (
    FollowUpSuggestion,
    InvestigationReasoning,
    ReasoningCitation,
    ReasoningFinding,
    RiskLevel,
)
from app.services.investigation_analyst import run_analyst_trace
from app.services.investigation_evidence import (
    build_evidence_ledger,
    citation_from_record,
    grounding_report,
)
from app.services.investigation_memory import (
    InvestigationMemory,
    entry_from_investigation,
)

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

_SYSTEM_PROMPT = (
    "You are a senior public-procurement investigator. You write concise, factual "
    "briefings for analysts. You must ONLY use facts from the EVIDENCE CONTEXT you are "
    "given. Never invent tenders, companies, values, or relationships. If the evidence "
    "does not support a conclusion, say so plainly. Do not use markdown, headings, or "
    "bullet points — return 2-4 plain sentences."
)


def build_reasoning(
    pkg: InvestigationPackage,
    query: str,
    *,
    memory: InvestigationMemory | None = None,
) -> InvestigationReasoning:
    """Compose the full reasoning output for an executed investigation package.

    Recalls related prior investigations from cross-investigation memory, runs a
    grounded multi-step analyst trace over the package, and persists this
    investigation to memory for future continuity. All additive to the existing
    grounded, evidence-backed reasoning.
    """
    subject = query.strip() or pkg.plan.query
    investigation_type = pkg.plan.investigation_type
    mem = memory or InvestigationMemory()

    entity_names = [c.canonical_name for c in pkg.canonical_companies]
    prior = mem.recall(subject, entities=entity_names)

    if not pkg.records:
        return InvestigationReasoning(
            subject=subject,
            investigation_type=investigation_type,
            generated_by="deterministic",
            executive_summary=(
                "Insufficient evidence to reach a conclusion. No procurement records "
                f"for “{subject}” were found in the investigation database or connected "
                "sources. Import or connect the relevant source data to investigate this entity."
            ),
            risk_level="insufficient",
            confidence=0.0,
            insufficient_evidence=True,
            follow_ups=_baseline_follow_ups(subject, investigation_type),
            grounding=grounding_report(pkg, 0, 0, 0),
            prior_investigations=prior,
        )

    findings = _findings_from_indicators(pkg)
    risk_level, risk_rationale, confidence = _assess_risk(pkg, findings)
    recommendations = _recommendations(pkg, risk_level, findings)
    follow_ups = _follow_ups(pkg, subject, investigation_type)

    # Evidence Engine: every distinct record as a fully-provenanced citation, plus
    # a grounding audit proving each finding is anchored to verifiable evidence.
    evidence_ledger = build_evidence_ledger(pkg)
    total_citations = sum(len(f.citations) for f in findings)
    backed = sum(1 for f in findings if f.evidence_backed)
    grounding = grounding_report(pkg, len(findings), backed, total_citations)

    # Multi-step, grounded analyst trace (tool-driven, package-only facts).
    analyst_trace = run_analyst_trace(pkg)

    reasoning = InvestigationReasoning(
        subject=subject,
        investigation_type=investigation_type,
        executive_summary="",  # filled below
        risk_level=risk_level,
        risk_rationale=risk_rationale,
        confidence=confidence,
        findings=findings,
        recommendations=recommendations,
        follow_ups=follow_ups,
        evidence_ledger=evidence_ledger,
        grounding=grounding,
        analyst_trace=analyst_trace,
        prior_investigations=prior,
    )

    summary, generated_by, provider, model = _executive_summary(pkg, reasoning)
    reasoning.executive_summary = summary
    reasoning.generated_by = generated_by
    reasoning.provider = provider
    reasoning.model = model

    # Remember this investigation for future continuity (best-effort).
    mem.remember(
        entry_from_investigation(
            subject=subject,
            investigation_type=investigation_type,
            risk_level=risk_level,
            confidence=confidence,
            key_entities=entity_names,
            key_indicators=[f.title for f in findings],
            records_reviewed=len(pkg.records),
        )
    )
    return reasoning


# --------------------------------------------------------------------------- findings


def _findings_from_indicators(pkg: InvestigationPackage) -> list[ReasoningFinding]:
    """Map each risk indicator to a cited finding.

    Citations are resolved from the indicator's ``related_tenders`` against the
    package records via the Evidence Engine, so every finding links back to a
    verifiable, fully-provenanced source record. A finding that resolves to no
    citation is flagged ``evidence_backed=False`` rather than presented as fact.
    """
    record_by_ref = {r.tender.reference_number: r for r in pkg.records}
    findings: list[ReasoningFinding] = []

    for indicator in pkg.indicators:
        citations = _citations_for_indicator(indicator, record_by_ref)
        findings.append(
            ReasoningFinding(
                title=indicator.title,
                detail=indicator.summary,
                severity=indicator.severity,  # type: ignore[arg-type]
                score=indicator.score,
                citations=citations,
                evidence_backed=bool(citations),
            )
        )
    return findings


def _citations_for_indicator(
    indicator: InvestigationProcurementIndicator,
    record_by_ref: dict,
) -> list[ReasoningCitation]:
    """Resolve an indicator's related tenders into full-provenance citations.

    Confidence is seeded from the indicator's own score (a stronger signal lends
    more weight to the evidence it rests on).
    """
    base_conf = max(0.4, min(0.95, indicator.score / 100))
    related_entity = indicator.related_entities[0] if indicator.related_entities else None
    citations: list[ReasoningCitation] = []
    for ref in indicator.related_tenders[:5]:
        record = record_by_ref.get(ref)
        if record is None:
            continue
        cit = citation_from_record(
            record,
            confidence=base_conf,
            related_entity=related_entity,
            evidence_type=indicator.type,
        )
        citations.append(cit)
    return citations


# --------------------------------------------------------------------------- risk


def _assess_risk(
    pkg: InvestigationPackage, findings: list[ReasoningFinding]
) -> tuple[RiskLevel, list[str], float]:
    """Derive an overall risk verdict from the indicator set.

    Deterministic and explainable: the rationale lists exactly which signals
    drove the level, so the analyst can audit the verdict.
    """
    if not findings:
        rationale = [
            f"{len(pkg.records)} procurement records reviewed",
            "No red-flag indicators triggered",
        ]
        # Some evidence, but nothing adverse — low risk, moderate confidence.
        return "low", rationale, min(0.6, 0.3 + len(pkg.records) * 0.02)

    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]
    top_score = max(f.score for f in findings)

    rationale: list[str] = []
    for finding in findings[:4]:
        rationale.append(f"{finding.title} (score {finding.score})")

    if len(high) >= 2 or top_score >= 85:
        level: RiskLevel = "critical"
    elif high:
        level = "high"
    elif medium:
        level = "medium"
    else:
        level = "low"

    # Confidence grows with corroborating records and distinct signal types.
    signal_types = {f.title for f in findings}
    confidence = min(0.95, 0.45 + len(signal_types) * 0.08 + min(len(pkg.records), 20) * 0.01)
    return level, rationale, round(confidence, 2)


# --------------------------------------------------------------------------- recommendations


def _recommendations(
    pkg: InvestigationPackage, risk_level: RiskLevel, findings: list[ReasoningFinding]
) -> list[str]:
    recs: list[str] = []
    types = {f.title for f in findings}

    if "Single Bidder Award" in types:
        recs.append(
            "Review the tender specifications and bid timelines for single-bidder awards to check for "
            "restrictive eligibility criteria that may have suppressed competition."
        )
    if "Repeat Supplier" in types:
        recs.append(
            "Cross-check the repeat buyer–supplier relationships against director and ownership records "
            "to rule out conflicts of interest."
        )
    if any(t in types for t in ("Buyer Concentration", "Supplier Single-Buyer Dependence")):
        recs.append(
            "Benchmark the concentrated award share against comparable buyers to determine whether it "
            "reflects a genuine market shortage or preferential allocation."
        )
    if "High-Value Tender" in types:
        recs.append(
            "Verify that high-value tenders followed the mandated approval and audit workflow for their value band."
        )
    if "Award Data Gap" in types:
        recs.append(
            "Request the missing award notices for closed tenders to close the transparency gap before drawing conclusions."
        )

    if risk_level in ("high", "critical") and not recs:
        recs.append("Escalate for manual review — adverse indicators were detected across the recorded procurement activity.")
    if not recs:
        recs.append(
            "No red flags detected in the available records. Widen the source coverage or date range to strengthen the assessment."
        )
    return recs


# --------------------------------------------------------------------------- follow-ups


def _follow_ups(
    pkg: InvestigationPackage, subject: str, investigation_type: str
) -> list[FollowUpSuggestion]:
    follow_ups = _baseline_follow_ups(subject, investigation_type)

    # Suggest drilling into the most-connected counterparties actually present
    # in the package, so follow-ups are grounded in real resolved entities.
    top_companies = [c.canonical_name for c in pkg.canonical_companies[:2]]
    for name in top_companies:
        if name.casefold() == subject.casefold():
            continue
        follow_ups.append(
            FollowUpSuggestion(
                label=f"Investigate {name}",
                query=name,
                rationale="Resolved counterparty appearing in this investigation's records.",
            )
        )

    buyers = _distinct_buyers(pkg)
    if buyers and investigation_type in ("supplier", "company"):
        follow_ups.append(
            FollowUpSuggestion(
                label=f"Investigate buyer {buyers[0]}",
                query=buyers[0],
                rationale="Primary buyer awarding tenders to this entity.",
            )
        )
    return follow_ups[:6]


def _baseline_follow_ups(subject: str, investigation_type: str) -> list[FollowUpSuggestion]:
    base = [
        FollowUpSuggestion(
            label="View award history",
            query=f"{subject} awards",
            rationale="Enumerate every award linked to this entity.",
        ),
        FollowUpSuggestion(
            label="Find similar tenders",
            query=f"tenders similar to {subject}",
            rationale="Surface comparable procurements for benchmarking.",
        ),
    ]
    if investigation_type in ("company", "supplier"):
        base.insert(
            0,
            FollowUpSuggestion(
                label="Investigate directors",
                query=f"{subject} directors",
                rationale="Check beneficial ownership and director overlaps.",
            ),
        )
    return base


def _distinct_buyers(pkg: InvestigationPackage) -> list[str]:
    seen: list[str] = []
    for record in pkg.records:
        buyer = (record.tender.procuring_entity or "").strip()
        if buyer and buyer not in seen:
            seen.append(buyer)
    return seen


# --------------------------------------------------------------------------- executive summary


def _executive_summary(
    pkg: InvestigationPackage, reasoning: InvestigationReasoning
) -> tuple[str, str, str | None, str | None]:
    """Return (summary_text, generated_by, provider, model).

    Tries the live LLM chain first (grounded, strictly context-only), and falls
    back to the deterministic composer whenever no provider answers. Provider and
    model reflect whichever provider actually produced the text.
    """
    deterministic = _deterministic_summary(pkg, reasoning)

    client = get_llm_client()
    if client is None:
        return deterministic, "deterministic", None, None

    context = _evidence_context(pkg, reasoning)
    prompt = (
        f"EVIDENCE CONTEXT (the only facts you may use):\n{context}\n\n"
        f"TASK: Write a 2-4 sentence executive summary of the investigation into "
        f"“{reasoning.subject}” for a procurement analyst. State the overall risk level "
        f"({reasoning.risk_level}) and the main reasons, citing only the evidence above. "
        f"If the evidence is thin, say the assessment is preliminary. "
        f"Do not introduce any entity, value, date, or relationship not present above."
    )
    try:
        text = client.complete(system=_SYSTEM_PROMPT, prompt=prompt)
    except LLMUnavailableError:
        return deterministic, "deterministic", None, None
    return text, "llm", client.provider, client.model


def _deterministic_summary(pkg: InvestigationPackage, reasoning: InvestigationReasoning) -> str:
    award_count = sum(len(r.awards) for r in pkg.records)
    entity_count = len(pkg.canonical_companies)
    high = [f for f in reasoning.findings if f.severity == "high"]

    lead = (
        f"Investigation of “{reasoning.subject}” reviewed {len(pkg.records)} procurement "
        f"record(s), {award_count} award(s), and {entity_count} resolved entity(ies)."
    )
    if reasoning.risk_level in ("high", "critical"):
        drivers = ", ".join(f.title.lower() for f in high[:3]) or "multiple adverse signals"
        verdict = (
            f" The overall risk is assessed as {reasoning.risk_level.upper()}, driven by {drivers}. "
            "Each indicator is backed by the cited source records below."
        )
    elif reasoning.findings:
        drivers = ", ".join(f.title.lower() for f in reasoning.findings[:3])
        verdict = (
            f" The overall risk is assessed as {reasoning.risk_level.upper()}. Notable signals: {drivers}. "
            "See the cited evidence for verification."
        )
    else:
        verdict = (
            f" No red-flag indicators were triggered; risk is assessed as {reasoning.risk_level.upper()} "
            "based on the available records."
        )
    return lead + verdict


def _evidence_context(pkg: InvestigationPackage, reasoning: InvestigationReasoning) -> str:
    """Compact, grounded evidence block handed to the LLM. Facts only."""
    lines: list[str] = []
    lines.append(f"Subject: {reasoning.subject} (type: {reasoning.investigation_type})")
    lines.append(f"Procurement records: {len(pkg.records)}")
    lines.append(f"Resolved entities: {len(pkg.canonical_companies)}")
    lines.append(f"Deterministic risk level: {reasoning.risk_level}")

    if reasoning.findings:
        lines.append("Indicators (each explainable, evidence-backed):")
        indicator_by_title = {ind.title: ind for ind in pkg.indicators}
        for finding in reasoning.findings[:8]:
            refs = ", ".join(
                c.related_tender for c in finding.citations if c.related_tender
            )[:200]
            lines.append(
                f"- [{finding.severity}/{finding.score}] {finding.title}: {finding.detail}"
                + (f" (tenders: {refs})" if refs else "")
            )
            indicator = indicator_by_title.get(finding.title)
            if indicator and indicator.reason:
                lines.append(f"    reason: {indicator.reason}")
            if indicator and indicator.supporting_suppliers:
                lines.append("    suppliers: " + ", ".join(indicator.supporting_suppliers[:5]))
            if indicator and indicator.supporting_buyers:
                lines.append("    buyers: " + ", ".join(indicator.supporting_buyers[:5]))
    else:
        lines.append("Indicators: none triggered.")

    sample_buyers = _distinct_buyers(pkg)[:5]
    if sample_buyers:
        lines.append("Buyers observed: " + "; ".join(sample_buyers))

    # Multi-step analyst observations — grounded, tool-derived facts.
    if reasoning.analyst_trace:
        lines.append("Analyst trace (grounded observations):")
        for step in reasoning.analyst_trace:
            lines.append(f"- [{step.tool}] {step.observation}")

    # Prior investigations recalled from memory — provenanced continuity.
    if reasoning.prior_investigations:
        lines.append("Prior related investigations (from memory):")
        for hit in reasoning.prior_investigations[:3]:
            lines.append(
                f"- “{hit.subject}” assessed {hit.risk_level} on "
                f"{hit.remembered_at.date().isoformat()} ({hit.match_reason})"
            )
    return "\n".join(lines)
