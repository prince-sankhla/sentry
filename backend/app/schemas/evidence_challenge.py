"""Evidence Challenge — SENTRY actively challenges its own findings.

For every major deterministic finding, the challenge asks: "what evidence would
prove this finding wrong?" It lists ONLY evidence-backed legitimate explanations
(never invented, never guessed), pairs each with the verification questions that
would eliminate or confirm it, and closes at a fixed decision boundary — never
"this is corruption", never "this is normal".

The challenge is organizational and read-only: it can never change an indicator,
a severity, or a risk score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# The fixed decision boundary. SENTRY never concludes in either direction.
CURRENT_POSITION = (
    "The available evidence does not yet distinguish between routine procurement "
    "activity and procurement requiring escalation. Additional evidence is required."
)


class LegitimateExplanation(BaseModel):
    """A possible benign reading of the finding, backed by evidence in the package.

    ``evidence`` states the deterministic fact that makes this explanation
    plausible here (dates, terms, structure found in the records) — an
    explanation with no in-package evidence is never listed.
    """

    explanation: str
    evidence: str
    records: list[str] = Field(default_factory=list)


class VerificationQuestion(BaseModel):
    """One question the investigator must answer to test the finding.

    ``eliminates`` names the legitimate explanation this question would confirm
    or eliminate — every question exists to kill exactly one hypothesis.
    """

    question: str
    eliminates: str


class FindingChallenge(BaseModel):
    """The challenge attached to one deterministic finding."""

    finding_id: str
    finding_name: str
    severity: str
    explanations: list[LegitimateExplanation] = Field(default_factory=list)
    questions: list[VerificationQuestion] = Field(default_factory=list)
    position: str = CURRENT_POSITION


class EvidenceChallenge(BaseModel):
    """Per-finding challenges for the whole investigation."""

    challenges: list[FindingChallenge] = Field(default_factory=list)
    principle: str = (
        "SENTRY does not try to persuade the investigator that it is correct — it "
        "helps the investigator discover whether it is wrong. Explanations are listed "
        "only when the retrieved records contain evidence for them; every question "
        "eliminates one explanation; no challenge ever alters a finding, severity, "
        "or score."
    )
