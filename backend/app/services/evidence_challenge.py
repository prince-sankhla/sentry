"""Build the Evidence Challenge — "what evidence would prove this finding wrong?"

Runs strictly AFTER deterministic findings and the Investigator Review.

The engine is context-agnostic: it knows nothing about financial year-end,
framework agreements, emergencies, or any other procurement context. For each
triggered indicator it asks the Context Plugin Registry which plugins can
logically apply, runs each plugin's deterministic evidence collection, and
assembles the challenge from whatever evidence-backed explanations come back:

    Evidence Challenge Engine
        → Context Plugin Registry
        → discover applicable plugins
        → run plugins (read-only, evidence-backed or nothing)
        → collect explanations + their eliminating questions
        → build the Evidence Challenge

Adding a new procurement context requires ONE new plugin file under
``app/services/context_plugins`` — this engine never changes.

Read-only by construction: plugins and engine receive the finished package and
never mutate indicators, severities, or scores.
"""

from __future__ import annotations

from app.schemas.evidence_challenge import (
    EvidenceChallenge,
    FindingChallenge,
    LegitimateExplanation,
    VerificationQuestion,
)
from app.schemas.investigation_executor import InvestigationPackage
from app.services.context_plugins.registry import applicable_plugins


def build_evidence_challenge(pkg: InvestigationPackage) -> EvidenceChallenge:
    """Challenge every triggered finding. Pure, deterministic, read-only."""
    challenge = EvidenceChallenge()
    rv2 = pkg.risk_assessment_v2
    if rv2 is None:
        return challenge

    for ind in rv2.indicators:
        explanations: list[LegitimateExplanation] = []
        questions: list[VerificationQuestion] = []

        for plugin in applicable_plugins(ind.id):
            found = plugin.collect_evidence(pkg, ind)
            if found is None:
                continue  # no in-package evidence → the explanation is NOT listed
            explanations.append(found)
            for q in plugin.verification_questions():
                questions.append(VerificationQuestion(question=q, eliminates=found.explanation))

        if not explanations:
            # No evidence-backed benign reading was detected. Say so honestly and
            # fall back to the finding's discriminating checklist so the
            # investigator still knows what to establish first.
            from app.services.investigator_review import _GENERIC_REQUIRED, _REQUIRED_BY_INDICATOR

            for q in _REQUIRED_BY_INDICATOR.get(ind.id, _GENERIC_REQUIRED)[:4]:
                questions.append(VerificationQuestion(
                    question=q,
                    eliminates="(no evidence-backed legitimate explanation detected — establish the basic facts first)",
                ))

        challenge.challenges.append(FindingChallenge(
            finding_id=ind.id,
            finding_name=ind.name,
            severity=ind.severity,
            explanations=explanations,
            questions=questions,
        ))

    return challenge
