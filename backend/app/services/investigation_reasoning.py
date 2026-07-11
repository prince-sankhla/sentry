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

import logging

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
from app.schemas.investigation_risk import RiskAssessmentV2
from app.services.investigation_analyst import run_analyst_trace
from app.services.investigation_evidence import (
    build_evidence_ledger,
    build_evidence_packet,
    citation_from_record,
    grounding_report,
)
from app.services.investigation_grounding import verify_summary
from app.services.investigation_integrity import assess_integrity
from app.services.investigation_report import build_analyst_report
from app.services.investigation_memory import (
    InvestigationMemory,
    entry_from_investigation,
)
from app.services.risk_engine import assess_risk_v2

logger = logging.getLogger(__name__)

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

    # SINGLE SOURCE OF TRUTH — Deterministic Risk Engine V2. The executor already
    # computes and attaches the V2 assessment during package finalisation; we only
    # recompute it here if this package was built outside the executor (e.g. a
    # direct build_reasoning call in a test). Overall severity, score, and
    # confidence ALL flow from V2 so the risk reported by the engine, the
    # reasoning layer, the LLM narrative, and the frontend can never diverge.
    # Resolved BEFORE findings so each finding can carry V2's evidence-verification
    # verdict (verified/probable/unknown).
    risk_v2 = pkg.risk_assessment_v2 or assess_risk_v2(pkg)
    pkg.risk_assessment_v2 = risk_v2

    findings = _findings_from_indicators(pkg)

    # The weighted integrity model remains as an explanatory sub-breakdown, but it
    # is NO LONGER the risk verdict — V2 is. Kept for backward-compatible detail
    # only; it never overrides the V2 severity or confidence below.
    integrity = assess_integrity(pkg)

    risk_level = risk_v2.overall_severity
    confidence = risk_v2.confidence.score if risk_v2.confidence else integrity.confidence
    risk_rationale = _risk_rationale_v2(risk_v2) or [
        f"{len(pkg.records)} records reviewed; no adverse integrity patterns dominated"
    ]

    recommendations = _recommendations(pkg, risk_level, findings)
    follow_ups = _follow_ups(pkg, subject, investigation_type)

    # Evidence Engine: every distinct record as a fully-provenanced citation, plus
    # a grounding audit proving each finding is anchored to verifiable evidence.
    evidence_ledger = build_evidence_ledger(pkg)
    total_citations = sum(len(f.citations) for f in findings)
    backed = sum(1 for f in findings if f.evidence_backed)
    verified = sum(1 for f in findings if f.verification == "verified")
    grounding = grounding_report(pkg, len(findings), backed, total_citations, verified)

    # Multi-step, grounded analyst trace (tool-driven, package-only facts).
    analyst_trace = run_analyst_trace(pkg)

    # Structured analyst-report sections — grounded deterministic projections
    # (buyer/supplier/award/timeline analysis, patterns, contradictions, missing
    # evidence, derived confidence). The LLM narrates these; it never computes them.
    analyst_report = build_analyst_report(pkg, grounding)
    # Headline confidence stays the Risk Engine V2 confidence (single source of
    # truth). The analyst report's multidimensional confidence assessment remains
    # available as a detailed breakdown card, but it does NOT override the verdict
    # confidence — that would reintroduce a second, divergent confidence number.

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
        integrity_assessment=integrity,
        analyst_report=analyst_report,
    )

    summary, generated_by, provider, model, fallback_reason = _executive_summary(pkg, reasoning)
    reasoning.executive_summary = summary
    reasoning.generated_by = generated_by
    reasoning.provider = provider
    reasoning.model = model
    reasoning.fallback_reason = fallback_reason

    # Consolidated proof bundle — every finding tied to its verification status and
    # provenanced evidence, assembled once the narrative provenance is known.
    reasoning.evidence_packet = build_evidence_packet(
        pkg, findings, subject=subject, risk_level=risk_level, generated_by=generated_by,
    )

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
    """Group indicators into one finding per type — never repeated titles.

    Detectors emit one indicator per affected record, so "Abnormal Contract
    Value" can fire a dozen times. Presenting a dozen identical findings is poor
    analyst UX, so identical types are collapsed into a single finding that
    carries the occurrence count, every supporting record, the merged
    provenanced citations, and per-instance summaries for drill-down.

    Citations resolve from each indicator's ``related_tenders`` via the Evidence
    Engine, so every grouped finding still links back to verifiable sources; a
    group that resolves to no citation is flagged ``evidence_backed=False``.
    """
    record_by_ref = {r.tender.reference_number: r for r in pkg.records}

    # Deterministic evidence-verification verdict per indicator type, from the
    # Risk Engine V2 evidence validator (verified/probable/unknown). This is the
    # authoritative "is this proven?" signal — surfaced onto each finding below so
    # a finding is labelled *verified* only when the backend proved its evidence,
    # not merely because a citation resolved. Best-effort: absent V2 (e.g. a
    # direct build in a test) leaves findings at their citation-derived status.
    verification_by_type: dict[str, str] = {}
    risk_v2 = pkg.risk_assessment_v2
    if risk_v2 is not None:
        verification_by_type = {ind.id: ind.evidence_status for ind in risk_v2.indicators}

    # Preserve first-seen order of indicator types (indicators arrive sorted by
    # score desc, so the strongest type leads).
    groups: dict[str, list[InvestigationProcurementIndicator]] = {}
    for indicator in pkg.indicators:
        groups.setdefault(indicator.type, []).append(indicator)

    findings: list[ReasoningFinding] = []
    for indicator_type, members in groups.items():
        lead = max(members, key=lambda i: (i.score, i.confidence))

        # Merge, de-duplicate and cap citations across every instance in the group.
        seen_cit: set[tuple[str, str | None]] = set()
        citations: list[ReasoningCitation] = []
        for member in members:
            for cit in _citations_for_indicator(member, record_by_ref):
                key = (cit.source_name, cit.related_tender)
                if key in seen_cit:
                    continue
                seen_cit.add(key)
                citations.append(cit)

        supporting_records = sorted({ref for m in members for ref in m.related_tenders})
        occurrences = len(members)
        severity = _dominant_severity(members)

        title = _pluralize_title(lead.title) if occurrences > 1 else lead.title
        if occurrences > 1:
            detail = f"{lead.summary} ({occurrences} occurrences across {len(supporting_records)} records)."
        else:
            detail = lead.summary

        # A finding with no resolvable citation is unverified regardless of the
        # engine's status; otherwise it inherits the deterministic V2 verdict.
        if not citations:
            verification = "unverified"
        else:
            verification = verification_by_type.get(indicator_type, "probable")

        findings.append(
            ReasoningFinding(
                title=title,
                detail=detail,
                severity=severity,  # type: ignore[arg-type]
                score=lead.score,
                citations=citations[:12],
                evidence_backed=bool(citations),
                verification=verification,  # type: ignore[arg-type]
                indicator_type=indicator_type,
                occurrences=occurrences,
                supporting_records=supporting_records,
                instances=[m.summary for m in members][:20],
            )
        )

    # Strongest findings first (grouped, so each type appears exactly once).
    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 0), f.score), reverse=True)
    return findings


def _dominant_severity(members: list[InvestigationProcurementIndicator]) -> str:
    """Highest severity present in the group (high > medium > low)."""
    order = {"low": 1, "medium": 2, "high": 3}
    return max((m.severity for m in members), key=lambda s: order.get(s, 0))


def _pluralize_title(title: str) -> str:
    """Best-effort plural for a grouped finding title (analyst-facing)."""
    if title.endswith(("s", "Timing", "Concentration", "Dependence", "Gap")):
        return title
    # e.g. "Abnormal Contract Value" -> "Abnormal Contract Values"
    return title + "s"


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


# Overall risk is produced by the Deterministic Risk Engine V2
# (``services/risk_engine.assess_risk_v2``): named rule-combination patterns over
# evidence-validated indicators. It is the single authoritative risk model — the
# reasoning layer narrates it and never recomputes it. The weighted integrity
# assessment survives only as an explanatory factor breakdown.


def _risk_rationale_v2(risk_v2: RiskAssessmentV2) -> list[str]:
    """Analyst-reasoning chips derived from the Risk Engine V2 assessment.

    Leads with named patterns (the strongest deterministic signal), then the top
    contributing indicators — so the frontend "Analyst reasoning" chips and the
    LLM context both narrate V2 structure rather than legacy integrity factors.
    """
    lines: list[str] = []
    for pattern in risk_v2.patterns[:4]:
        lines.append(f"{pattern.name} [{pattern.severity}] — {pattern.rule}")
    for indicator in risk_v2.indicators:
        if len(lines) >= 6:
            break
        lines.append(f"{indicator.name} [{indicator.severity}] — {indicator.reason}")
    return lines[:6]


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
) -> tuple[str, str, str | None, str | None, str | None]:
    """Return (summary_text, generated_by, provider, model, fallback_reason).

    Tries the live LLM chain first (grounded, strictly context-only), and falls
    back to the deterministic composer whenever no provider answers, every
    provider errors/refuses, or the model's phrasing fails the grounding guard.
    ``fallback_reason`` records which of those occurred (``None`` on LLM success)
    so the UI can show *why* the deterministic composer authored the summary
    instead of silently reading as "Fallback Active".
    """
    deterministic = _deterministic_summary(pkg, reasoning)

    client = get_llm_client()
    if client is None:
        return deterministic, "deterministic", None, None, "no_provider"

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
    except LLMUnavailableError as exc:
        # Every configured provider failed, errored, or returned a restricted /
        # refusal response — that is never shown; the deterministic composer answers.
        # Surface the reason instead of silently falling back.
        logger.warning("LLM reasoning fell back to deterministic (provider error): %s", exc)
        return deterministic, "deterministic", None, None, "provider_error"

    # Grounding guard: the model may only *phrase* the summary, never introduce
    # facts. Reject any output that asserts a quantity (value, share, count) not
    # present in the evidence context and fall back to the deterministic composer,
    # which is grounded by construction. Correctness beats phrasing.
    verdict = verify_summary(text, context)
    if not verdict.grounded:
        logger.warning(
            "LLM summary from %s failed the grounding guard (%s); using deterministic composer",
            client.provider, verdict.reason,
        )
        return deterministic, "deterministic", client.provider, client.model, "grounding_guard"
    return text.strip(), "llm", client.provider, client.model, None


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

    # Risk Engine V2 is the authoritative risk model — hand the LLM its severity,
    # named patterns, and confidence so the narrative NARRATES V2 rather than
    # recomputing risk from raw indicators. The model may only phrase this.
    risk_v2 = pkg.risk_assessment_v2
    if risk_v2 is not None:
        lines.append(
            f"Risk Engine V2 verdict: {risk_v2.overall_severity} "
            f"(score {risk_v2.overall_score}/100, deterministic — do not recompute)."
        )
        if risk_v2.patterns:
            lines.append("Risk patterns (deterministic rule combinations):")
            for pattern in risk_v2.patterns[:5]:
                lines.append(f"- [{pattern.severity}] {pattern.name}: {pattern.rule}")
        if risk_v2.confidence is not None:
            lines.append(
                f"Risk Engine V2 confidence: {int(risk_v2.confidence.score * 100)}% "
                f"({risk_v2.confidence.level})."
            )

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

    # Grounded structured-report facts so the narrative can reflect contradictions
    # and the derived confidence — all computed deterministically from the package.
    report = reasoning.analyst_report
    if report is not None:
        if report.confidence_assessment is not None:
            ca = report.confidence_assessment
            lines.append(f"Derived confidence: {int(ca.score * 100)}% ({ca.level}).")
        if report.contradictions:
            lines.append("Contradictions detected (deterministic):")
            for c in report.contradictions[:5]:
                lines.append(f"- [{c.severity}] {c.summary}")
        if report.missing_evidence:
            lines.append("Evidence gaps: " + "; ".join(report.missing_evidence[:3]))
    return "\n".join(lines)
