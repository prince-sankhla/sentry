# SENTRY — Demo Engineering Report (3-minute judge demo)

> **Scope:** presentation only. UI, backend, and investigation logic are **frozen**.
> This report optimizes *what the presenter does and says*, nothing else.
>
> **Definition of Done:** a first-time judge understands SENTRY in 3 minutes and
> remembers **one** thing for the rest of the day:
>
> ## 🎯 "I clicked a red flag and landed on the official government document."
>
> Every decision below is subordinate to that one sentence.

---

## 1. The optimal 180-second flow (mental walkthrough)

Three core clicks. Nothing else is required. Each click answers exactly one question
the judge is silently asking.

| Time | Presenter action | The question it answers | What the judge sees | Trust delta |
|---|---|---|---|---|
| 0:00–0:15 | Land on Command Center. **Don't touch the dashboard.** | "What is this?" | Analyst board + a single accent banner: *Case #001 · Dharmagarh NAC*. | Sets frame: real system, real case. |
| 0:15–0:20 | **Click ① the Case #001 banner.** | "Show me a real investigation." | Pipeline strip begins streaming. | Commitment: a specific, named, real case. |
| 0:20–1:00 | Narrate while the **pipeline streams**. No clicks. | "Is this real work, or a chatbot?" | Steps stream: resolve entity → retrieve records → resolve → **run risk engine** → reason. | Peak process-trust: visible, auditable work. |
| 1:00–1:25 | Results land on the **verdict header**. Read the badge. | "What did it conclude?" | **MEDIUM risk**, confidence, 4 numbers, Export button. | Honesty: "medium — review," not "critical." |
| 1:25–1:45 | Scroll to **The finding** (risk indicators). Read the fragmentation flag aloud. | "What exactly is wrong?" | *Contract Fragmentation (medium)* + *Missing Award*, each with **"View official record →"**. | Specificity: a concrete, visual pattern. |
| 1:45–2:20 | **Click ② "View official record →"** on the fragmentation flag. **PAUSE.** | "Is this real / from the government?" | A live **tendersodisha.gov.in** tender notice opens. | 🏆 **THE MOMENT.** Red flag → government document. |
| 2:20–2:45 | Return to SENTRY. **Click ③ "Export evidence packet."** | "Can an investigator act on this?" | A print-ready 15-section dossier in a new tab. | Deliverable: court-ready output, one click. |
| 2:45–3:00 | Close on the one-paragraph pitch. | "Why does this matter?" | Packet on screen. | The takeaway lands. |

**Click budget: 3.** Banner → red flag → export. That is the entire demo.

---

## 2. What we cut, and why

**Cut clicks (never navigate here on the happy path):**
- ❌ The **relationship graph** — beautiful, but it eats 20–30s of panning and answers no
  question the judge asked. *Keep it in your pocket for "can you visualize connections?"*
- ❌ **Web procurement evidence**, **Resolved companies**, **Recommendations**,
  **Suggested investigations** — all real, all below the fold. Do not scroll to them.
- ❌ **Settings / Profile / Timeline / Risk / Reports** nav pages — off-story.
- ❌ The **AI Investigation panel / Analyst trace / Grounding** — below the "AI summary ·
  optional" divider *by design*. Only reach it if a judge asks "does it use AI?"

**Cut words (say less, mean more):**
- ❌ Don't narrate KPIs, deltas, or the map. The dashboard is B-roll — 15 seconds, silent.
- ❌ Don't read the raw buyer string `Municipal Bodies||Dharmagarh NAC` aloud. Say **"Dharmagarh."**
- ❌ Don't say "corruption," "fraud," or "guilty." The engine says **"requires review."** So do you.
- ❌ Don't explain the architecture unprompted. The pipeline *shows* it; let it.

**Cut animations/waiting:**
- The pipeline stream is the one animation that earns its seconds — it *is* the trust.
  Everything else (card fades, graph physics) should not be dwelt on. Don't wait for motion
  to finish before speaking.

**Cut panels from your attention (not from the app — the UI is frozen):**
- Everything except: **banner → pipeline → verdict header → the finding → the source link →
  export.** If it's not on that path, it doesn't exist for these 3 minutes.

---

## 3. Optimal presenter script (verbatim — ~430 words, ~180s)

> **[0:00 — landing, don't touch anything]**
> "SENTRY turns real government procurement into defensible investigations. Everything here is
> built from actual tenders scraped from government portals. This is the analyst's board — but a
> dashboard isn't an investigation. Let me open a real case."

> **[0:15 — click ① the Case #001 banner]**
> "This is Case #001 — Dharmagarh, a municipal body in Odisha."

> **[0:20 — pipeline streaming, don't click]**
> "Watch what it's doing. This is not a chatbot. It resolves the entity, **retrieves the actual
> tender records**, runs a **deterministic risk engine** — published integrity rules, not a model
> guessing — and only then reasons over what it found. Every step is real work you can audit."

> **[1:00 — verdict header lands]**
> "Here's the verdict: **medium risk** — flagged for review, *not* a determination of wrongdoing.
> One buyer, a same-day batch of ward-works tenders under a single tender notice, about **1.3 crore
> rupees**. And every number here is a link to the records behind it."

> **[1:25 — scroll to The finding, read the flag]**
> "This is what fired: **contract fragmentation**. Sixteen tenders, published on the same day,
> closing on the same day, under one NIT — several priced just under the threshold that would force
> open competitive bidding, and **two of them are priced identically to the rupee**. That's a
> textbook requirement-splitting signature. Now — is any of this real?"

> **[1:45 — click ② "View official record →" on the flag. PAUSE 2 seconds.]**
> "There it is. The **actual tender, on the Odisha government procurement portal.** From a risk flag,
> to the official government record, in one click. That's the difference between an AI that *claims*
> corruption and a platform that *shows you the record* and lets you decide."

> **[2:20 — return to SENTRY, click ③ Export evidence packet]**
> "And one click gives an investigator the whole case — a court-ready packet: the timeline, every
> supporting tender with its source URL, the confidence, **what we don't know**, and even the
> innocent explanations a reviewer must weigh."

> **[2:45 — close]**
> "Real records. Deterministic rules. Every figure traced to an official source. It never accuses —
> it hands an investigator **evidence they can act on.** Thank you."

---

## 4. Expected judge questions → best **technical** answers

**Q: "Is this real data or seeded?"**
> "Real. Sixteen live notices on Odisha's e-procurement portal — the link you just saw goes straight
> to the government record. We also store the captured page at ingestion, so it reproduces even if
> the portal rotates the link."

**Q: "Is the AI deciding this is corrupt?"**
> "No — deliberately. A **deterministic risk engine** applies published rules — fragmentation,
> missing award, single-bidder. Same records + same rules = same result on every run. The AI only
> writes prose over findings the engine already grounded, and a grounding guard blocks it if it
> strays. Turn the AI off and the finding is identical."

**Q: "How do you know it's fragmentation and not just normal batch tendering?"**
> "We don't claim it is — that's why it's **medium and 'requires review.'** The pattern is a
> recognized red flag (World Bank / OCP / CVC guidance on splitting of works), but the packet lists
> the lawful explanations too. We surface *where to look*; a human decides."

**Q: "Can I reproduce the result?"**
> "Yes. Every figure regenerates from content-hashed raw storage, and every claim cites a tender by
> reference number with a source URL. It's auditable, not a black box."

**Q: "Why medium and not critical? Looks serious."**
> "Because the honest signal is medium. Single-bidder and buyer-equals-supplier typologies **did not
> fire** — this is tender-stage data with no award records yet. We show that as *missing evidence*,
> not exoneration. A tool that screamed 'critical' here would be lying to you."

**Q: "How does it scale / how many sources?"**
> "The pipeline is source-agnostic — India's central portal, state systems like Odisha, World Bank,
> Prozorro. Today is one verified case; the same planner → executor → risk engine runs on all of them."

**Q: "What about false positives?"**
> "Designed for false-positive-first. Precision retrieval only pulls records that directly reference
> the entity, the engine downgrades on thin evidence, and every flag ships with its benign
> explanations. We optimize for *defensible leads*, not volume."

---

## 5. Expected judge questions → best **business** answers

**Q: "Who's the customer / who pays for this?"**
> "Oversight bodies, audit institutions, investigative journalists, and anti-corruption units.
> Today they read PDFs by hand; SENTRY hands them a triaged, evidence-backed lead with the source
> already attached — the work product they'd otherwise spend days assembling."

**Q: "What's the wedge / where do you start?"**
> "One country, one pattern, done credibly. India's procurement portals are public and huge.
> We land with fragmentation and single-bidder detection — the most cited, most defensible red
> flags — then expand typologies and sources."

**Q: "What's novel vs. a BI dashboard or a keyword alert?"**
> "A dashboard shows aggregates; an alert shows a keyword. SENTRY produces a **single defensible
> finding with a full evidence chain to the official source and a court-ready packet** — that's what
> an investigator actually files. Dashboards don't do that."

**Q: "Why now?"**
> "Procurement data is finally open and machine-readable (OCDS), and integrity rules are published.
> The missing piece was turning them into *defensible, sourced findings* — that's us."

**Q: "What's the risk / liability of flagging entities?"**
> "It's the core design constraint. SENTRY never declares wrongdoing — it flags patterns for human
> review, in writing, with the innocent explanations attached. Buyers (public bodies), not named
> private firms, are the demo subjects. The restraint is the product."

**Q: "How is this defensible in court / to an editor?"**
> "Every figure traces to a government URL, the packet documents methodology and what's missing, and
> the result is deterministic and reproducible. It's built to survive scrutiny, not to generate headlines."

---

## 6. Failure recovery (internet / backend / portal fails)

**Golden rule: never debug in front of judges.** Every failure has one sentence that turns it into
a feature — say it, then move to backup. Practiced calm > working software.

| Failure | Live recovery line + action |
|---|---|
| **Investigation spins / SSE stalls** | Wait 5s max. "Live system — here's the completed case," → play the **backup video (§8)**. Never sit on a spinner. |
| **Record count is 17, not 16** (Chatrapur NAC — a second "Municipal Bodies" buyer — appears) | Expected; verified in the data. Say: "sixteen of these were filed as **one same-day batch under a single NIT**," and click the fragmentation flag. Don't claim the screen shows exactly 16. |
| **`tendersodisha.gov.in` won't load / link expired** | "The portal rotates session links — which is exactly why we capture the source at ingestion." → show the Evidence Ledger card's stored source metadata + `source_record_id`. **The wow still lands.** |
| **Evidence packet is slow** (it re-runs the pipeline) | You warmed it in pre-flight. If cold: "it's regenerating the full packet from source live," → wait, or open the pre-saved PDF. |
| **LLM provider errors** | Nothing to do — the panel falls back to a deterministic report. "The AI was unavailable, so it fell back to a safe evidence-composed report — by design." |
| **Backend fully down** | Go straight to the **backup video + screenshot deck (§8)**. Do not restart live. |
| **Judge grabs the keyboard, types a random word** | "Let me point it at a real entity — that's how an analyst uses it," → retype a verified buyer. Keep keyboard control. |
| **Wi-Fi dies entirely** | Run everything **local on the presenting laptop** (§7), or narrate over the backup video. Rehearse this once so it's a non-event. |

---

## 7. Demo rehearsal checklist (the day/night before)

- [ ] Run the **full 3-minute script end-to-end at least 5 times**, out loud, on the real laptop.
- [ ] **Lock the launcher query** and **know your record count** (16 vs 17). Decide your fragmentation
      line accordingly. If you want a tighter set, test the NIT id `2026_ORULB_132524` or select the
      buyer from the entity dropdown.
- [ ] Confirm the fragmentation flag's **"View official record →"** opens a **live** `tendersodisha.gov.in`
      page. This is the demo — rehearse this click until it's muscle memory.
- [ ] **Warm the evidence packet** (open it once) so it's cached and instant.
- [ ] Decide **LLM ON or OFF and lock it.** Deterministic is more defensible; if the LLM is flaky, OFF.
- [ ] **Record a clean 60–90s run** as the offline backup video. Rehearse narrating over it (muted).
- [ ] Build the **5-screenshot deck** (pipeline / verdict MEDIUM / the finding / red-flag→portal / packet).
- [ ] Time yourself. If you're over 3:00, cut words from Act 1, not from the source click.
- [ ] Rehearse **one full run with Wi-Fi off** (local backend + video). Make a dead network a non-event.
- [ ] Practice the **failure lines (§6)** aloud so they're reflexive, not improvised.

---

## 8. Final demo checklist (T-minus 30 minutes → showtime)

**Environment**
- [ ] Backend healthy: `GET /api/analytics/overview` returns 200, non-zero.
- [ ] Postgres up with Odisha data imported; run Case #001 once to warm caches.
- [ ] Evidence packet warmed (opened once).
- [ ] LLM mode locked (ON/OFF decided).

**Machine**
- [ ] Browser full-screen, 110–125% zoom, **one tab**, cache warm.
- [ ] Notifications, Slack, dev tools, command palette — **all closed.**
- [ ] Laptop charged + plugged in; screen sleep disabled.
- [ ] Backup video + screenshot deck open in a background window, ready.

**Content**
- [ ] Numbers memorized: **16 tenders · one NIT · ~₹1.32 crore · MEDIUM · Odisha.**
- [ ] The three clicks rehearsed: **banner → "View official record" → export.**
- [ ] The one sentence loaded: *"a red flag to the official government record in one click."*

**On stage**
- [ ] Speak to the **judge**, not the screen.
- [ ] After the source page opens: **stop talking for two seconds.** Let it land.
- [ ] Never say "corruption." Always "flagged for review."
- [ ] If anything breaks: one recovery sentence (§6), then backup. Never debug live.

---

## Appendix — verified case facts (say these, they're all defensible)

- **Subject:** Dharmagarh Notified Area Council, Kalahandi district, **Odisha**.
- **Source:** Odisha e-Procurement portal, `tendersodisha.gov.in` (live state government system).
- **Pattern:** **16 works tenders**, one same-day batch under NIT **`2026_ORULB_132524`** —
  published **2026-06-22**, all closing **2026-07-08**.
- **Value:** **₹1,32,45,762 (~₹1.32 crore)**.
- **Signature:** two identical-value pairs (**₹16,94,915 ×2** and **₹8,47,458 ×2**), and
  **₹16,94,915 = exactly 2 × ₹8,47,458** — a common estimation template, not independent scoping.
- **Verdict:** **MEDIUM (50/100), confidence 0.60** — *Contract Fragmentation* + *Missing Award*.
  **Not critical.** No award/entity typologies fired (tender-stage data). **An oversight lead,
  not an allegation.**
- **Data caveat (know before stage):** the dataset holds two `Municipal Bodies` buyers — Dharmagarh
  (16) and **Chatrapur (1)** — so the query may return **17** records. The finding is the 16-tender
  NIT batch regardless.

---

*Nothing in the product changed for this report. The only thing engineered here is the three
minutes — so that a first-time judge understands SENTRY completely, and remembers the one
investigation that took them from a red flag to a government document in a single click.*
