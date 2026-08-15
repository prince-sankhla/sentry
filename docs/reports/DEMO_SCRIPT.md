# SENTRY — CASE #001 Demo Script (3 minutes)

> **Role:** Demo Director. **The one thing the judge must believe by minute three:**
> **"This platform investigates *real* government procurement and shows me the evidence — down to the official source — without ever accusing anyone."**
>
> The investigation is the hero. The UI is supporting evidence. We win on **one click from a
> risk flag to the official government record**, and on the discipline to say **"medium — review this,"**
> not "corruption." That restraint *is* the pitch: it's what separates an intelligence platform from a
> hype demo.

---

## 0. CASE #001 — chosen from REAL, VERIFIED data

**Subject:** **Dharmagarh NAC** — Dharmagarh Notified Area Council, Kalahandi district, Odisha.
**Source:** Odisha e‑Procurement portal (`tendersodisha.gov.in`) — a live state government system.
**Why this case wins:** it is the **first end‑to‑end verified Indian investigation** (see `CASE_001.md`),
regenerates deterministically from raw storage, and every figure below resolves to a public government URL.

| Property | Value | Why it wins |
|---|---|---|
| What was detected | **16 works tenders published as one same‑day batch** under a single NIT `2026_ORULB_132524` | A clean, visual, *explainable* pattern — no jargon needed. |
| Total value | **₹1,32,45,762 (~₹1.32 crore)** | Concrete, memorable, real. |
| The signature | Published **2026‑06‑22**, all closing **2026‑07‑08**; **two identical‑value pairs** (₹16,94,915 ×2 and ₹8,47,458 ×2), and **₹16,94,915 = exactly 2 × ₹8,47,458** | The judge can *see* the pattern with their own eyes. |
| Risk verdict | **MEDIUM (50/100), confidence 0.60** — *Contract Fragmentation* + *Missing Award* | **Not "critical."** This is our credibility — the engine grades honestly. |
| Framing | **Oversight lead requiring manual review — NOT an allegation** | Aligned with the constitution: SENTRY never declares wrongdoing. |
| Provenance | **16 live `tendersodisha.gov.in` notices**, one per tender | The "Original" link is the wow. |

> **Why MEDIUM is a feature, not a weakness.** Municipal batch tendering is *often lawful*. The engine
> says so — it lists benign explanations and the missing evidence right in the packet. A platform that
> flagged this "CRITICAL 95%" would be lying. **We show the judge a tool that refuses to cry wolf.**

**Backup case (identical flow, if Dharmagarh underperforms on the day):** any other verified buyer that
returns a clean batch. Swap the name in the search box; the script is identical. **Never** demo a named
private company as high‑risk — buyers only.

---

## 1. Brutal pre‑flight (do this 30 min before, every time)

The demo depends on **backend + Postgres (with the Odisha data imported) + optional LLM** being up.
Treat this as a launch checklist — if any item fails, go to the **Offline Backup (§6)**.

- [ ] **Backend healthy:** `GET /api/analytics/overview` returns 200 with non‑zero totals.
- [ ] **LOCK THE QUERY + KNOW THE RECORD COUNT (most important).** The landing "Open Case #001" button runs
      **`Dharmagarh NAC`**. Run it twice end‑to‑end and confirm **MEDIUM risk**, indicators
      **`contract_fragmentation`** + **`missing_award_data`**, and an Evidence Ledger with the
      **`tendersodisha.gov.in`** "Original" links.
      **Expect ~16–17 records, not necessarily exactly 16.** In the imported Odisha data there are *two*
      `Municipal Bodies` buyers — **Dharmagarh NAC (the 16‑tender batch we want)** and **Chatrapur NAC (1
      unrelated tender)** — and because the resolver canonicalizes both to the shared first segment
      "Municipal Bodies," the query can pull the lone **Chatrapur** record in alongside the 16.
      **This is fine:** the finding *is* the 16‑tender same‑day batch under NIT `2026_ORULB_132524`; one
      extra record doesn't change the story. **Verify what actually renders and pick your line:**
      - If exactly **16** → say "sixteen tenders, one NIT" and don't mention the count issue.
      - If **17** (a Chatrapur row appears) → say "sixteen of these were filed as one same‑day batch under a
        single NIT" and click **"Records"** to show the batch. Do **not** claim the screen shows exactly 16.
      - Cleaner alternatives if you want a tight 16: try the NIT id **`2026_ORULB_132524`** as the query, or
        select the buyer from the entity dropdown — whichever yields the tightest set on the day. To change
        the launcher default, edit the `launchFollowUp("Dharmagarh NAC")` call in
        `frontend/src/app/investigation-workspace.tsx`.
- [ ] **Warm the Evidence Packet.** The "Export evidence packet" button opens a new tab that **re‑runs the
      pipeline** (a few seconds). Open it once during pre‑flight so it's cached and instant on stage.
- [ ] **Provider badge:** decide **LLM ON or OFF and lock it.** Deterministic is *more* defensible
      ("no AI hallucination"). If the LLM is flaky, **demo with it OFF** — the finding is identical.
- [ ] Browser: full‑screen, 110–125% zoom, one tab, cache warm.
- [ ] **Screen‑record a clean run now** as the offline backup video (§6).
- [ ] Close the command palette, notifications, dev tools.

---

## 2. The 3‑minute run — second by second

Total **~180s**. Four acts: **Board (20s) → Investigation (70s) → Evidence→Source (70s) → Packet + Close (20s)**.

### ACT 1 — The board (0:00–0:20)

**Presenter clicks:** nothing yet. Lands on the Command Center.
**Judge sees:** the analyst's board — morning brief, KPI row, India map, live activity. Then a single
accent‑bordered banner: **"Case #001 · Dharmagarh NAC — Odisha ward‑works procurement · 16 same‑day
tenders · ₹1.32 crore · contract‑fragmentation pattern."**

**You say:**
> "SENTRY turns real government procurement into defensible investigations. Everything here is built from
> **actual tenders scraped from government portals** — India's central portal and state e‑procurement
> systems. This is the board. But a dashboard isn't an investigation. Let me open a real case."

**Presenter clicks:** the **Case #001** banner.
**Expected reaction:** *"OK, show me."* — you've promised a specific, named, real case.

> 🎯 Keep Act 1 to 20 seconds. The dashboard is B‑roll. Do **not** narrate KPIs one by one.

### ACT 2 — The investigation (0:20–1:30)

**Judge sees:** the **live pipeline strip** streams, step by step, with a progress rail:
`Resolving canonical entity → Understanding request & selecting sources → Retrieving procurement records
→ Resolving entities → Running risk engine → Reasoning & generating findings.`

**You say (while it streams — this is the trust moment):**
> "Watch the pipeline. It is **not** calling a chatbot. It resolves the entity, **retrieves the actual
> tender records**, runs a **deterministic risk engine** — published integrity rules, not a model
> guessing — and only then reasons over what it found. Every step is real work you can audit."

**Judge sees:** results land. The **verdict header** is the hero: the subject, a **MEDIUM risk** badge with
**confidence**, four headline numbers — **Records · Awards · Awarded value ₹1.32 Cr · Risk indicators** —
and an **Export evidence packet** button.

**You say:**
> "The verdict: **medium risk** — flagged for review, *not* a determination of wrongdoing. One municipal
> buyer, a same‑day batch of ward‑works tenders under a single NIT, ₹1.32 crore. And every number here is a link."

**Presenter clicks:** the **"Records"** stat card → the page **smooth‑scrolls to the tender records** (the
16‑tender NIT batch).
**Expected reaction:** *"Nice — the number is the evidence."* (Reinforces: nothing here is decorative.)

**Presenter clicks:** the **"Risk indicators"** stat → scrolls to **The finding**. Two deterministic
indicators: **Contract Fragmentation (medium)** and **Missing Award (medium)**, each with its record count
and a **"requires review"** tag.

**You say:**
> "Here's what fired: **contract fragmentation** — sixteen tenders published and closing on the *same two
> days* under one NIT, several near competitive‑bidding thresholds, with **two identical‑value pairs**. And
> a **missing‑award** gap — none has a published winner yet. Note the language: **'requires review,'** never
> 'corrupt.' The machine hands the analyst the pattern; the human makes the call."

> 🎯 Optional 10‑second spectacle: scroll to the **Investigation graph** — buyer, 16 tenders, indicators,
> evidence, all linked. Click **one** indicator node, then move on. Don't get lost panning.

### ACT 3 — Evidence → official source = THE WOW MOMENT (1:30–2:40)

**Presenter scrolls to:** the **Evidence Ledger**.
**Judge sees:** a grid of provenance cards — each with a **quality tier** (Primary), a **★ score**, a
**confidence %**, publication/retrieval dates, the related tender reference, and actions: **Original**,
**Cite**, **Why trusted**.

**You say:**
> "This is the heart of SENTRY — the **evidence ledger**. Every claim in that finding traces to a card here.
> Quality tier, confidence, publication date on record."

**Presenter clicks:** **"Why trusted"** on a Primary card.
**Judge sees:** plain‑language reasons — *Primary‑tier source, publicly linkable, prioritised Indian
procurement source, publication date on record.*

**Presenter clicks:** **"Original"** on that card → it opens the **live `tendersodisha.gov.in` tender notice.**

> 🏆 **THIS IS THE WOW MOMENT. Pause. Let it land.**

**You say:**
> "And there it is — the **actual tender on the Odisha government procurement portal.** From a risk flag, to
> the evidence, to the **official government source, in two clicks.** That's the difference between an AI
> that *claims* corruption and a platform that *shows you the record* and lets you decide."

**Presenter clicks:** **"Cite"** on the card.
> "One click puts a court‑ready citation on my clipboard."

### ACT 4 — Evidence packet + close (2:40–3:00)

**Presenter clicks:** **"Export evidence packet."**
**Judge sees:** a new tab with a **self‑contained, print‑ready dossier** — 15 sections: methodology,
timeline, triggered typologies, every supporting tender + document + **official source URL**, evidence
confidence, **missing evidence**, **alternative (benign) explanations**, and a **manual verification
checklist.** One button: **Print → PDF.**

**You say (close):**
> "One click produces the whole case as a court‑ready packet — including what we *don't* know and the
> innocent explanations a reviewer must weigh. **Real records. Deterministic rules. Every figure traced to
> an official source. And it never accuses — it hands an investigator defensible, evidence‑backed leads.**
> Thank you."

> The AI narrative lives **below** everything, behind an **"AI summary · optional"** divider. Mention it
> only if asked (§4): *"the finding stands without any AI — the model only writes prose over evidence the
> engine already grounded."*

---

## 3. What is the hero, and what to HIDE

**Hero (spend your seconds here):**
1. The **live pipeline** streaming — proves real work, not a chatbot.
2. **Evidence Ledger → "Original" → `tendersodisha.gov.in`** — the two‑click proof.
3. **MEDIUM + "requires review"** + the packet's benign‑explanation / missing‑evidence sections — proves
   intellectual honesty. This is the winning differentiator.
4. **Clickable headline numbers** — "16 records" jumps to the 16 records. Nothing is decorative.

**Hide / avoid (these lose the room):**
- ❌ **Never let a judge type a random word** ("Water", "Road"). Generic keywords can over‑fire the risk
   engine — the #1 credibility landmine. Keep the keyboard; if pressed, type **another verified buyer**.
- ❌ **Settings / Profile** pages — thin, off‑story.
- ❌ Don't read the raw canonical buyer string with `||` separators aloud — say **"Dharmagarh NAC."**
- ❌ Don't stake the wow on a fast external page load. If the portal is slow, fall back to the captured
   evidence: *"we store the source at ingestion, so the evidence survives even if the portal rotates the link."*
- ❌ Don't over‑explain the graph. It's spectacle, not substance — 10 seconds max.

---

## 4. Likely judge questions → best answers

**Q: "Is this real data or seeded/fake?"**
> "Real. Sixteen live notices on Odisha's e‑procurement portal — that 'Original' link goes straight to the
> government record. We also store the captured page at ingestion, so it's reproducible even if the portal
> rotates the link."

**Q: "So is this corruption?"**
> "No — and we're deliberate about that. It's a **medium‑risk oversight lead.** Batch tendering of ward
> works is often perfectly lawful. The engine even lists the innocent explanations and the missing evidence
> in the packet. It says **'review this,'** never 'corrupt.' A human investigator decides."

**Q: "Then why flag it at all?"**
> "Because splitting one programme of works into many same‑day, sub‑threshold lots is a **recognised red
> flag** — World Bank, OCP, and CVC guidance on 'splitting of works.' Two identical‑value pairs and a clean
> 2× value relationship are worth a human look. We surface *where to look*, with the evidence attached."

**Q: "Is the AI deciding this?"**
> "No. A **deterministic risk engine** applies published rules — fragmentation, missing award. Same records
> + same rules = same result, every run. The AI only narrates grounded findings and is blocked by a
> grounding guard if it strays. Turn it off and the finding is identical."

**Q: "Can I reproduce it?"**
> "Yes. Every figure regenerates from content‑hashed raw storage, and every claim cites a source record by
> ID with a link. Click 'Cite' for the full reference. It's auditable, not a black box."

**Q: "What about single‑bidder / buyer‑equals‑supplier detection?"**
> "The engine tested those and they **did not fire** — this is tender‑stage data with no award records yet.
> We show that honestly as *missing evidence*, not as exoneration. Ingest the award pages and those
> typologies run on this exact batch."

**Q: "How does it scale?"**
> "The pipeline is source‑agnostic — India's central portal, state systems like Odisha, World Bank,
> Prozorro. Today is one verified case; the same planner → executor → risk engine runs on all of them."

**Q: "What's novel vs. a BI dashboard?"**
> "A dashboard shows aggregates. SENTRY produces a **single defensible finding with a full evidence chain to
> the official source and a court‑ready packet** — that's what an investigator actually files."

---

## 5. Failure scenarios (and the live recovery line)

| Failure | On‑stage recovery |
|---|---|
| Investigation spins / SSE stalls | Wait 5s max. *"Live system — here's the completed case,"* → **Offline Backup (§6).** Never sit on a spinner. |
| Query returns the wrong record set / too many | Don't argue with the screen. *"Let me point it at the exact buyer,"* → retype **`Dharmagarh`** or select from the dropdown (pre‑verified in §1). |
| Returns **insufficient / low** | *"Good — it won't cry wolf on thin evidence,"* → switch to the pre‑verified backup buyer or the video. |
| `tendersodisha.gov.in` won't load | *"The portal rotates session links — which is exactly why we capture the source at ingestion,"* → show the card's stored metadata + `source_record_id`. |
| Evidence packet slow (re‑runs pipeline) | You warmed it in pre‑flight. If cold: *"it's regenerating the full packet from source live,"* → wait, or show the pre‑saved PDF. |
| LLM errors mid‑run | Nothing to do — the panel falls back to a deterministic report. *"The AI was unavailable, so it fell back to a safe evidence‑composed report — by design."* |
| Backend fully down | Go straight to **§6.** Never restart live. |

**Golden rule:** never debug in front of judges. Every failure has a *sentence* that turns it into a
feature, then you move to backup. Practiced calm > working software.

---

## 6. Offline backup plan (MANDATORY — build during pre‑flight)

Prepare **all three**, in order of preference:

1. **Screen recording** of a clean Case #001 run (60–90s, muted; narrate live over it). Your primary net.
2. **Local run:** frontend + backend + seeded Postgres on the **presenting laptop** — no conference Wi‑Fi
   dependency. The frontend degrades gracefully, but the *investigation* needs the backend + DB local.
3. **Screenshot deck (5 stills):** (1) pipeline streaming, (2) verdict header MEDIUM + 16 records,
   (3) the finding (fragmentation + missing award), (4) Evidence Ledger "Why trusted" + Original,
   (5) the `tendersodisha.gov.in` source page — **or** the exported packet. Tell the whole story from stills in 90s.

> Rehearse **once fully offline** (video + narration) so a dead network is a non‑event.

---

## 7. One‑paragraph pitch (memorize — your raft if tech fails entirely)

> "SENTRY turns public procurement into defensible investigations. It ingests real tenders from government
> portals, resolves entities, and runs a **deterministic risk engine** — fragmentation, single‑bidder,
> concentration, timing. Case #001: **Dharmagarh Notified Area Council in Odisha published sixteen ward‑works
> tenders as one same‑day batch, ₹1.32 crore, with two identical‑value pairs** — a textbook
> requirement‑splitting signature. SENTRY graded it **medium — requires review, not an allegation**, and
> traced **every figure to the official Odisha portal in two clicks**, then exported a court‑ready packet
> that even lists the innocent explanations. That's the product — not corruption detection, **evidence you
> can act on.**"

---

## 8. Demo Director's notes (what's world‑class, what to manage)

**World‑class — keep, don't touch:**
- The **Evidence Ledger** (`evidence-ledger.tsx`) — tiers, stars, "why trusted", one‑click Cite,
  Original/PDF links. This *is* the pitch.
- The **streaming pipeline** — the single best "this is real work" signal.
- The **medium‑risk, oversight‑lead framing** + the packet's missing‑evidence / benign‑explanation sections —
  perfectly aligned with the constitution and the strongest trust signal you have.

**Manage in the run, don't rebuild:**
- **Query resolution** — buyers canonicalize to their shared first pipe‑segment ("Municipal Bodies"), so
  `Dharmagarh NAC` can also pull the lone **Chatrapur NAC** record (→ 17, not 16). **Verified in the raw
  data.** Know your record count before you walk on stage and pick your line (§1). The *finding* — the
  16‑tender same‑day NIT batch — is unaffected.
- **Generic‑keyword over‑firing** — control the keyboard; never let a judge type free text.
- **External link fragility** — never bet the wow on a live third‑party page; the captured source is the fallback.
- **Packet regenerates live** — warm it in pre‑flight.

**The one sentence that wins or loses this:** *from a medium‑risk flag to the official government source in
two clicks — and it refuses to call it corruption.* Rehearse those two clicks until they're muscle memory.
