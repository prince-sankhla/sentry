# SENTRY — Hackathon Demo Runbook

## Recommended 3–5 minute flow

### 1. Start with the question
Open `/investigate?q=Dharmagarh%20NAC`.

Frame SENTRY as an investigation workspace, not a score dashboard: the system starts from a procurement subject and assembles grounded records, indicators, evidence and provenance.

### 2. Show the evidence boundary
Open `/verification?q=Dharmagarh%20NAC`.

Show the distinction between source-backed evidence, evidence quality, missing evidence and reasoning. Avoid presenting a confidence value as proof.

### 3. Connect the records
Open `/graph` and, where useful, `/timeline`.

Demonstrate the buyer → tender → award → supplier/document/evidence ecosystem and the chronological sequence of procurement events. State clearly that graph connectivity is a review lead, not a misconduct finding.

### 4. Challenge before escalating
Return to the investigation and show the finding case file / evidence challenge surface.

Call out the legitimate alternative explanations and the exact evidence still required. This is the key false-positive-control story.

### 5. Prepare official review
Open `/review?q=Dharmagarh%20NAC`.

Show the structured handoff: subject, review leads, evidence volume, open evidence requests, alternative explanations and reviewer note.

### 6. Switch to Government / Audit
Use the role switcher and open `/review/inbox`, then `/cases`.

Show the transition from review intake to a human case lifecycle: open → under review → evidence requested → monitoring / escalated / closed.

## What not to claim during the demo

- SENTRY does not adjudicate wrongdoing.
- A red flag or risk score is not proof of misconduct.
- Missing data is not automatically negative evidence.
- The current review inbox and case board are workflow prototypes stored locally in the browser; they are not a shared government system of record.
- Monitoring surfaces are refreshable snapshots unless a live upstream connector is explicitly active.
- International methodology or context is not Indian law.

## Judge takeaway

SENTRY's differentiation is the complete evidence chain:

**Detect → Contextualize → Connect → Compare → Challenge → Corroborate → Verify → Prioritize → Human Decision.**

The product reduces investigator reconstruction work while keeping provenance, uncertainty and accountability visible.
