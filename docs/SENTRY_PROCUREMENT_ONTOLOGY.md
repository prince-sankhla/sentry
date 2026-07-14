# SENTRY Procurement Ontology

## Book III — The Semantic Constitution (v1.0)

> **Purpose.** This Book defines *what things exist* in the procurement world
> SENTRY reasons about, and *how they relate* — independent of any storage
> engine, query language, or program. It is the shared vocabulary that Knowledge
> Graph V2, the Risk Engine, Entity Resolution, the Investigation Planner,
> Explainability, AI Reasoning, Search, and Graph Analytics must all speak.
>
> **Scope discipline.** This Book models *procurement reality*, never software.
> It contains no code, no APIs, no schemas-of-a-database, no query syntax. Where
> Book II (Engineering Constitution) fixed the *rules* and their IDs, Book III
> fixes the *nouns and verbs* those rules operate on. Book II §12 (Ontology
> Mapping) is the binding contract between the two; this Book fulfils it.

### Provenance legend

Every substantive claim is tagged so an auditor can separate settled science from
domain fact from our own design choices. **We never present an architectural
choice as an established standard, and never invent a legal requirement.**

| Tag | Meaning |
|-----|---------|
| `[ONT]`  | Universally accepted knowledge-representation / ontology-engineering principle |
| `[DOM]`  | Procurement domain knowledge (incl. internationally recognized data models: OCDS, and anti-corruption frameworks: FATF beneficial-ownership, OECD integrity) |
| `[ARCH]` | SENTRY architectural recommendation (this platform's design, not an external norm) |

---

## Chapter 1 — Core Ontology Principles

### 1.1 The ontology represents reality, not the application

`[ONT]` An ontology is a *shared conceptualization of a domain*. Its test of
correctness is fidelity to the world, not convenience for a program. A tender
existed as a real economic act before SENTRY ingested it and will remain
meaningful after any particular subsystem is rewritten. Therefore the ontology
must name **procurement realities** (a tender, an award, a beneficial owner, a
signing event) and never software artifacts (a table, a record, a cache, a job).

**Consequence `[ARCH]`.** If a concept only exists because of how we *store* or
*compute* something, it does not belong in this Book. If a concept would still be
true were SENTRY switched off, it probably does.

### 1.2 The nine concept classes are never mixed

`[ARCH]` The domain decomposes into nine **disjoint** top-level concept classes.
An individual thing belongs to exactly one. Keeping them separate is what makes
the graph explainable and auditable.

| # | Concept class | Answers the question | Examples |
|---|---------------|----------------------|----------|
| 1 | **Agents** | *Who acts?* | Company, Natural Person, Ministry, PSU |
| 2 | **Roles** | *In what capacity?* | Buyer, Supplier, Bidder, Auditor |
| 3 | **Objects** | *What is being procured / transacted?* | Tender, Lot, Bid, Award, Contract |
| 4 | **Events** | *What happened, and when?* | Publication, Closing, Award Issued, Contract Signed |
| 5 | **Documents** | *What was published/recorded?* | Tender notice, BoQ, Award letter, MCA filing |
| 6 | **Evidence** | *What grounds a claim?* | An evidence node linking a document/source to an assertion |
| 7 | **Indicators** | *What integrity signal was observed?* | Single Bidder, GST Overlap (Book I / Book II IDs) |
| 8 | **Patterns** | *What combination of signals?* | Systemic Suppression, Related-Party (Book II PAT-*) |
| 9 | **Analytics** | *What are we doing about it?* | Investigation, Finding, Recommendation, Report |

Plus two **cross-cutting** modelling layers that qualify the above rather than
compete with them: **Identifiers** (Chapter 5) and **Time** (Chapter 6).

### 1.3 Reification: events and evidence are first-class

`[ONT]` A naïve model hangs facts as properties on entities ("tender.awardDate").
This loses the ability to attach provenance, confidence, contradiction, and time
to the *fact itself*. SENTRY therefore **reifies**:

* An **Event** is a node, not a date-attribute — so we can say *who reported it*,
  *when we learned it*, and *how sure we are*.
* **Evidence** is a node, not a footnote — so every assertion in the graph points
  to the source that justifies it (Chapter 7).

This single principle is what lets Explainability trace any score to a source
(Book II §6) and lets confidence be computed from evidence quality (Book II §5).

### 1.4 Agents vs. Roles — the identity/capacity split

`[DOM]` `[ONT]` A single legal person may be a **Buyer** in one procurement and a
**Supplier** in another; a PSU procures *and* bids. Modelling "Buyer" and
"Supplier" as fixed entity types would make the same company two unrelated nodes
and blind us to exactly the conflicts we hunt. So an **Agent** (a legal or
natural person that persists across procurements) is separated from the **Role**
it *plays within a specific procurement context*. This directly enables the
`buyer ≡ supplier` indicator (Book II `REL-007`): it is the detection that one
Agent holds two conflicting Roles in one process. This mirrors the Open
Contracting Data Standard's *parties + roles* design `[DOM]`.

### 1.5 Open-world, monotonic, append-only

`[ONT]` The graph is **open-world**: absence of an edge means "unknown", not
"false". Missing an award record does not assert "no award happened" — it asserts
"no award *observed*", which is itself an investigable signal (Book II `COMP-003`).
Knowledge is added, **never overwritten** (Chapter 6). A correction is a *new,
later assertion*, not a mutation of the old one.

### 1.6 Provenance-first

`[ARCH]` Every assertion carries, at minimum: the **source** it came from, the
**time it was asserted**, and a **confidence**. An assertion with no provenance is
not admissible to the graph. This is the ontological expression of SENTRY's
oversight mandate — no fact without a source.

### 1.7 Neutrality of naming

`[ARCH]` Ontology terms are descriptive, never accusatory. There is a
`RelatedPartyIndicator`, never a `FraudEntity`; a `SingleBidderEvent`, never a
`RiggedTender`. Judgement lives in investigators, not in node labels. This keeps
the semantic layer legally defensible for a decade.

---

## Chapter 2 — Entity Taxonomy

Entities are the **nouns**. Below, each is defined by its *identity criterion*
(what makes two instances the same) and its *essential attributes* (intrinsic
facts, not computed scores). Computed/analytical values never live on domain
entities — they live in the Analytics layer (Chapter 8–9).

### 2.1 Agent layer — *who acts*

`[DOM]` Agents persist across procurements and carry identifiers (Chapter 5).

| Entity | Identity criterion | Essential attributes | Notes |
|--------|--------------------|-----------------------|-------|
| **LegalEntity** (Company) | Registration identifier (CIN/company number) | legal name, incorporation date, legal form, status (active/struck-off), registered jurisdiction | Superclass of commercial suppliers and corporate buyers. |
| **NaturalPerson** | Personal identifier (DIN/passport/national ID) — privacy-scoped | name, associated identifiers | Directors, beneficial owners, signatories. Privacy rules in Ch.10 of Book II apply. |
| **GovernmentBody** | Official designation + parent hierarchy | official name, tier, parent body | Superclass of the public-sector agents below. |
| ↳ **Ministry** | Government designation | — | Apex public buyer. `[DOM]` |
| ↳ **Department** | Parent ministry + name | — | |
| ↳ **PSU** (Public Sector Undertaking) | CIN *and* government ownership | ownership %, administrative ministry | Dual nature: a company **and** a public body — can procure and supply. Drives `FP-04`. `[DOM]` |
| ↳ **StateAgency / StatePSU** | State + designation | state | |
| ↳ **LocalBody** | Jurisdiction + name | tier (municipal/panchayat) | |
| ↳ **RegulatoryAuthority** | Statutory designation | mandate | e.g. procurement regulator, publisher of notices. |
| ↳ **Auditor** | Designation | mandate | Oversight agent (e.g. supreme audit institution). `[DOM]` |
| ↳ **Court / Tribunal** | Designation | jurisdiction | For dispute/debarment linkage. |

### 2.2 Role layer — *in what capacity* (Chapter 1.4)

`[DOM]` A Role is an Agent's capacity **within a specific procurement context**.
Roles are always scoped to an Object or Process; they never float free.

| Role | Played by | Scoped to |
|------|-----------|-----------|
| **ProcuringEntity / Buyer** | GovernmentBody or LegalEntity | a Tender / Contracting Process |
| **Supplier / Vendor** | LegalEntity (or consortium) | an Award / Contract |
| **Bidder** | LegalEntity | a Bid on a Tender/Lot |
| **Consortium / JointVenture member** | LegalEntity | a Bid/Award (composite bidder) `[DOM]` |
| **Subcontractor** | LegalEntity | a Contract |
| **TenderAuthority / Publisher** | GovernmentBody | a Document/Notice |
| **BeneficialOwnerRole** | NaturalPerson | a LegalEntity (see 2.3) |

### 2.3 Ownership & governance layer

`[DOM]` These model corporate control — the substrate of related-party risk.

| Entity/Role | Meaning |
|-------------|---------|
| **Director** | A NaturalPerson holding a directorship in a LegalEntity (identified by DIN). |
| **Shareholder** | An Agent holding equity in a LegalEntity (may itself be a company — enabling ownership chains). |
| **BeneficialOwner** | The NaturalPerson who ultimately owns/controls a LegalEntity, possibly through layers. Aligns with FATF's Ultimate Beneficial Owner concept. `[DOM]` |
| **Signatory** | A NaturalPerson authorized to sign for an Agent. |

### 2.4 Object layer — *the procurement process and its parts*

`[DOM]` This is the OCDS-aligned spine: a **Contracting Process** is the umbrella
under which tender → award → contract stages unfold.

| Entity | Identity criterion | Essential attributes |
|--------|--------------------|-----------------------|
| **ContractingProcess** | Process identifier (portal ID) | title, procurement method, category, jurisdiction, funding source |
| **Tender** | Tender reference within a process | reference number, title, description, estimated value, currency, method, publication/closing (as Events) |
| **Lot** | Tender + lot number | lot title, lot value | A Tender may be divided into Lots, each separately awarded. `[DOM]` |
| **Bid** | Tender/Lot + bidder | submitted value, status | Often unavailable in open data — modelled so it can be attached when present. |
| **Award** | Tender/Lot + supplier + date | awarded value, currency, status | The decision to select a supplier. |
| **Contract** | Award + contract identifier | contract value, signing (Event), period | The binding agreement following an award. `[DOM]` |
| **ContractAmendment** | Contract + sequence | change type, value delta, reason | Append-only variations (scope/value/time). `[DOM]` |
| **Milestone / Deliverable** | Contract + name | due date, status | Implementation-stage objects (OCDS *implementation*). `[DOM]` |
| **Payment** | Contract + sequence | amount, date | Implementation-stage financial flow. |

### 2.5 Classification layer — *how procurement is categorized*

| Entity | Meaning |
|--------|---------|
| **ProcurementMethod** | Open / Limited / Single-source (nomination) / Framework / e-Reverse-Auction / Emergency. A controlled vocabulary, jurisdiction-mapped (Ch.11). `[DOM]` |
| **ProductCategory (CPV-style)** | The classification of *what* is procured (goods/works/services taxonomy, e.g. UNSPSC/CPV). `[DOM]` |
| **Scheme / Programme** | A government scheme under which procurement occurs. `[DOM]` |
| **Project** | A capital project spanning many procurements. |
| **FundingSource** | Who funds it (domestic budget line, World Bank loan, ADB grant…). Drives jurisdiction rules (Ch.11). `[DOM]` |
| **FrameworkAgreement** | A pre-established multi-supplier arrangement from which call-offs are made; explains lawful single-supplier call-offs (`FP-05`). `[DOM]` |
| **EmergencyProcurementContext** | A qualifier marking a process as emergency/disaster-driven, explaining compressed timelines/single bidder (`FP-01/02`). `[DOM]` |

### 2.6 Identifier layer — *stable keys* (detailed in Ch.5)

`[DOM]` Modelled as first-class so they can carry validity, issuer, and
confidence: **CIN** (company), **DIN** (director), **GSTIN** (tax registration),
**PAN** (tax account), **companyNumber / DUNS / LEI** (international), plus a
generic **Identifier** superclass for future schemes.

### 2.7 Geospatial layer

| Entity | Meaning |
|--------|---------|
| **Address** | A postal address string + normalized components; a first-class node so shared addresses become edges (`REL-006`). `[ARCH]` |
| **Location** | A resolved place (point/region). |
| **Country / State / District** | Administrative hierarchy for jurisdiction and geo-analytics. |

### 2.8 Evidence, Document & Source layer (detailed in Ch.7)

**Source**, **Document**, **Evidence** — the provenance backbone.

### 2.9 Analytical layer (detailed in Ch.8–9)

**RiskIndicator**, **RiskPattern**, **Recommendation**, **Investigation**,
**Finding**, **Report** — kept strictly separate from domain entities so that
analysis never contaminates the record of reality.

### 2.10 Concepts a world-class model must add `[ARCH]`

Beyond the requested list, a decade-proof procurement ontology should include:

* **Debarment / Sanction** — an Agent's exclusion by an authority/court, with
  validity period. Critical context: a sanctioned supplier winning is a strong
  signal. `[DOM]`
* **Consortium/JointVenture** as a composite bidder (2.2) — otherwise related-party
  logic misses shared members.
* **Corrigendum / Amendment Notice** as a Document subtype — it lawfully explains
  timeline compression (`FP-03`).
* **Complaint / Bid-Protest / Dispute** — investigator-relevant procedural events.
* **Currency & FX rate** as first-class — cross-jurisdiction value comparison is
  impossible otherwise (Ch.11).
* **DataSource reliability tier** — feeds confidence dimension `CONF-002`.

---

## Chapter 3 — Relationship Taxonomy

Relationships are the **verbs**. Each is a *directed, typed, provenanced* edge.
Notation: `Subject —PREDICATE→ Object`. Every edge additionally carries the
metadata of Chapter 10 (source, confidence, validity, assertion time).

### 3.1 Process relationships `[DOM]`

```
Buyer(Role)        —CONDUCTS→         ContractingProcess
ContractingProcess —CONTAINS→         Tender
Tender             —DIVIDED_INTO→      Lot
Tender             —RECEIVES→          Bid
Bid                —SUBMITTED_BY→      Bidder(Role of LegalEntity)
Tender / Lot       —RESULTS_IN→        Award
Award              —GRANTED_TO→        Supplier(Role of LegalEntity)
Award              —FORMALIZED_AS→     Contract
Contract           —AMENDED_BY→        ContractAmendment
Contract           —HAS_MILESTONE→     Milestone
Contract           —SETTLED_BY→        Payment
```

### 3.2 Agent / ownership relationships `[DOM]`

```
LegalEntity   —GOVERNED_BY→        Director(NaturalPerson)
Director      —IDENTIFIED_BY→      DIN
LegalEntity   —OWNED_BY→           Shareholder(Agent)      (supports ownership chains)
LegalEntity   —ULTIMATELY_CONTROLLED_BY→ BeneficialOwner(NaturalPerson)
LegalEntity   —REGISTERED_AT→      Address
LegalEntity   —IDENTIFIED_BY→      CIN | GSTIN | PAN
LegalEntity   —PART_OF→            Consortium
GovernmentBody—PARENT_OF→          GovernmentBody          (ministry→dept→unit)
PSU           —ADMINISTERED_BY→    Ministry
Agent         —SANCTIONED_BY→      Authority/Court         (with validity period)
```

### 3.3 Classification relationships `[DOM]`

```
ContractingProcess —USES_METHOD→        ProcurementMethod
Tender             —CLASSIFIED_AS→      ProductCategory
ContractingProcess —FUNDED_BY→          FundingSource
ContractingProcess —UNDER_SCHEME→       Scheme
ContractingProcess —PART_OF_PROJECT→    Project
Award              —CALLED_OFF_FROM→     FrameworkAgreement
ContractingProcess —QUALIFIED_BY→        EmergencyProcurementContext
```

### 3.4 Evidence & document relationships `[ARCH]` `[ONT]`

```
Document   —PUBLISHED_BY→     Authority(Role)
Document   —OBTAINED_FROM→    Source
Evidence   —CITES→            Document
Evidence   —DRAWN_FROM→       Source
Evidence   —SUPPORTS→         (Event | Award | Indicator | any Assertion)
Award      —EVIDENCED_BY→     Evidence
Event      —EVIDENCED_BY→     Evidence
```

### 3.5 Analytical relationships `[ARCH]`

```
RiskIndicator   —OBSERVED_ON→        (Tender | Award | Agent | Buyer–Supplier pair)
RiskIndicator   —BACKED_BY→          Evidence
RiskPattern     —COMPOSED_OF→        RiskIndicator            (Book II §3)
RiskPattern     —ESCALATES→          RiskIndicator            (dependency edge, Book II §2)
Recommendation  —DERIVED_FROM→       RiskPattern | RiskIndicator
Recommendation  —REQUIRES_EVIDENCE→  DocumentType
Investigation   —ANALYZES→           Agent | ContractingProcess
Investigation   —SURFACED→           RiskIndicator
Investigation   —CONCLUDED_IN→       Finding
Finding         —GROUNDED_IN→        Evidence
Investigation   —PRODUCES→           Report
Report          —RECOMMENDS→         Recommendation
```

### 3.6 Temporal relationships `[ONT]`

```
(any Object)  —HAS_EVENT→   Event
Event         —OCCURRED_AT→  Time
Role          —VALID_DURING→ Interval        (e.g. Director appointed→resigned)
```

### 3.7 Relationship neutrality `[ARCH]`

No predicate asserts wrongdoing. `SHARES_DIRECTOR_WITH`, `AWARDED_REPEATEDLY_BY`,
and `SAME_ADDRESS_AS` are *structural*; interpretation is an Indicator (analytical
layer), never baked into the verb.

---

## Chapter 4 — Relationship Constraints

Constraints make the graph checkable and the analytics trustworthy. `[ONT]`

### 4.1 Cardinality

| Relationship | Cardinality | Rationale |
|--------------|-------------|-----------|
| ContractingProcess CONTAINS Tender | 1 → many | A process may re-tender. `[DOM]` |
| Tender DIVIDED_INTO Lot | 1 → many (optional) | Lots optional. |
| Tender RESULTS_IN Award | 1 → many (0..*) | Zero = award-data gap (`COMP-003`); many = multi-lot. |
| Award GRANTED_TO Supplier | many → 1, but Supplier may be a Consortium | One award, one (possibly composite) winner. |
| Award FORMALIZED_AS Contract | 1 → 0..1 | Contract may be absent in open data. |
| LegalEntity GOVERNED_BY Director | many ↔ many | Directors sit on multiple boards — the crux of `REL-005`. |
| LegalEntity IDENTIFIED_BY GSTIN | 1 → many | One firm, many state GSTINs; shared GSTIN across "distinct" firms = `REL-004`. `[DOM]` |
| LegalEntity ULTIMATELY_CONTROLLED_BY BeneficialOwner | many ↔ many | Layered control. |
| Indicator BACKED_BY Evidence | 1 → 1..* (required) | No unbacked indicator (Book II §6.3.1). |
| Pattern COMPOSED_OF Indicator | 1 → 2..* | A pattern is a *combination*. `[ARCH]` |

### 4.2 Optionality (required vs optional)

`[ARCH]` **Required** (their absence is itself a signal, never a silent gap):

* Every Tender must have a Buyer and a publication Event, or be flagged
  incomplete.
* Every Indicator must have ≥1 Evidence edge.
* Every Evidence must have a Source.

**Optional** (open-world; absence = unknown, not false): Bids, Contracts,
BeneficialOwners, Payments. Their absence may *trigger* an indicator but must
never be treated as a factual negative.

### 4.3 Temporal constraints `[ONT]`

* An Award Event must not precede its Tender's publication Event unless flagged
  (this *is* `TIME-001`). Constraints describe the norm so violations become
  detectable signals — they are **soft** (flag-and-investigate), never **hard**
  (reject-the-data). Rejecting anomalous data would delete the very evidence we
  seek. `[ARCH]`
* A Director's `VALID_DURING` interval bounds when their overlaps count toward a
  related-party pattern (an overlap only matters while both directorships were
  concurrent). `[DOM]`

### 4.4 Versioning & historicity `[ONT]`

* Every edge is **versioned** and **append-only** (Chapter 6). A superseded fact
  gains an end-of-validity assertion; it is never deleted.
* Entities support **identity versioning** (Chapter 5): a company that renames
  keeps one canonical identity across name versions.

### 4.5 Integrity invariants (must always hold) `[ARCH]`

1. No Role exists without an Agent playing it.
2. No analytical node (Indicator/Pattern/Recommendation) attaches directly to a
   raw Document without passing through Evidence.
3. No edge exists without provenance metadata (Ch.10).
4. Deleting is impossible; only asserting-an-end is permitted.

---

## Chapter 5 — Entity Identity

The hardest problem in a procurement graph is *sameness*: is "ACME Pvt Ltd",
"Acme Private Limited", and "ACME PVT. LTD." one supplier or three? Identity is
modelled explicitly, never assumed from a string. `[ARCH]` `[ONT]`

### 5.1 Canonical identity

Each real-world thing has one **CanonicalEntity** — a stable, opaque identity that
never changes even as names, addresses, and registrations evolve. All observed
mentions attach to it. The canonical identity is *not* a name; names are
attributes that come and go.

### 5.2 Preferred identifier hierarchy

`[DOM]` Identity resolution prefers **strong, issuer-backed identifiers** over
strings, in this order:

| Entity | Strongest key | Fallbacks |
|--------|--------------|-----------|
| Company | CIN (or national company number / LEI) | GSTIN → PAN → normalized name + address |
| Director / person | DIN (or national ID) | name + associated companies |
| Tender | Portal tender reference within its process | title + buyer + dates |
| Award | Tender + supplier + award date | award value + supplier |
| Document | Source URL + content hash | title + publication date |
| Evidence | Deterministic content signature | — |
| Buyer / Gov body | Official designation + hierarchy path | normalized name |

### 5.3 Aliases and name history

`[ARCH]` A CanonicalEntity holds a set of **Alias** assertions, each with: the
alias string, its source, and the validity interval during which it was in use.
This preserves *former names* so a historical tender naming the old name still
resolves to today's canonical entity.

### 5.4 Identity assertions carry confidence

`[ONT]` "Mention M refers to CanonicalEntity C" is itself a **provenanced,
confidence-bearing assertion**, not a hard fact. Weak matches (name-only) get low
confidence; identifier matches (CIN) get high. This confidence flows into
Book II's `CONF-004` (Entity Resolution) dimension.

### 5.5 Mergers, acquisitions, renames, splits

`[DOM]` `[ARCH]` Corporate change is modelled as **first-class identity events**,
append-only:

| Change | Modelled as |
|--------|-------------|
| **Rename** | A new Alias interval opens; canonical identity is unchanged. |
| **Merger** | `Entity A —MERGED_INTO→ Entity B` at time *t*; both identities persist; post-*t* activity attributes to B, pre-*t* to A. History is never rewritten. |
| **Acquisition** | An ownership-change event: `A —ACQUIRED_BY→ B` with date; control edges gain new validity intervals. |
| **Split / demerger** | `A —SPLIT_INTO→ {B, C}` at *t*. |
| **Erroneous merge (dedup fix)** | A *reversible* `SAME_AS`/`NOT_SAME_AS` assertion pair — because entity resolution is fallible, identity links must be *revisable without data loss*. `[ARCH]` |

**Constitutional rule `[ARCH]`.** Identity resolution decisions are *assertions
about the world*, so they are provenanced, versioned, and reversible — never
silent, destructive merges. A wrong merge must be undoable without losing the
original mentions.

---

## Chapter 6 — Temporal Model

`[ONT]` Time is not an attribute; it is a dimension of every fact. SENTRY uses a
**bitemporal** model, because auditability requires distinguishing *when
something was true in the world* from *when SENTRY learned it*.

### 6.1 Two timelines

| Timeline | Question | Example |
|----------|----------|---------|
| **Valid time** | When was this true in the real world? | The award was issued on 2023-04-10. |
| **Transaction / assertion time** | When did SENTRY come to know/record it? | We ingested that award on 2024-01-22. |

Every assertion carries both. This is what lets an investigator ask "*what did we
know, and when did we know it?*" — decisive for legal defensibility and for
replaying a past assessment (Book II §13, `GOV-009`).

### 6.2 Events are first-class (recap of 1.3)

`[DOM]` Procurement is a sequence of dated Events, each a node:

```
TenderPublished · TenderClosed · BidSubmitted · BidOpened · AwardIssued ·
ContractSigned · ContractAmended · MilestoneReached · PaymentMade ·
DirectorAppointed · DirectorResigned · CompanyIncorporated · CompanyStruckOff ·
SanctionImposed · SanctionLifted · DocumentPublished · EvidenceRetrieved ·
InvestigationStarted · InvestigationConcluded · IdentityMerged · IdentityRenamed
```

Each Event has a `type`, a valid-time (instant or interval), the object it
happened to, and provenance. Timeline-based indicators (`TIME-*`) read these
Events; they never read a mutable "date field".

### 6.3 Intervals and states

`[ONT]` Some facts are *states with duration*, not instants: a directorship
(appointed→resigned), a framework agreement's validity, a debarment period, an
alias's period of use. These are **Intervals**, and co-occurrence logic (Book II
IDM) is interval-aware: two directorships only "overlap" if their intervals
intersect.

### 6.4 Nothing is overwritten

`[ARCH]` The append-only rule (1.5) is enforced temporally: a "change" is a new
assertion with a later transaction-time and, usually, a new valid-time interval
that supersedes the prior one by *closing* it — the prior assertion remains
readable forever. The graph therefore supports **time-travel queries**: "show the
ownership structure as SENTRY understood it on any past date."

### 6.5 Temporal provenance of analysis `[ARCH]`

An Indicator/Pattern/Finding is stamped with the valid-time *and* assertion-time
of the evidence that produced it, so a re-run under a newer ruleset yields a *new*
analytical node rather than mutating the historical one (ties to Book II §13.5).

---

## Chapter 7 — Evidence Ontology

Evidence is the load-bearing wall of the entire platform. It is a **first-class
entity**, never a property. `[ARCH]` This chapter fulfils Book II §6's demand
that every score trace to a source.

### 7.1 The Source → Document → Evidence → Assertion chain

`[ONT]`

```
Source        the origin (a portal, a registry, an ingested dataset)
  └─ publishes/holds
Document      a concrete published artifact (notice, BoQ, award letter, filing)
      └─ is cited by
Evidence      a first-class node asserting "this document/source supports X"
          └─ supports
Assertion     an Event, Award, Indicator, Pattern, or any graph fact
```

### 7.2 Source

`[DOM]` A Source carries: identity, type (official portal / registry / aggregator
/ scraped / manual), and a **reliability tier**. The tier feeds Book II's
`CONF-002` (Source Reliability). Official primary sources outrank aggregators
outrank scraped pages — an evidentiary hierarchy that is itself part of Book I.

### 7.3 Document

`[DOM]` A Document carries: title, document type (tender notice, corrigendum,
BoQ, award letter, contract, MCA filing, GST record, court order…), publication
Event, issuing Authority, and a content signature enabling duplicate detection
(the substrate of `DOC-002`).

### 7.4 Evidence node

`[ARCH]` An Evidence node is the *reified justification*. It records:

* **What it supports** (the target assertion),
* **What it draws on** (Document(s) and/or Source),
* **Evidence status** — `verified` / `probable` / `unknown` (mirroring Book II's
  evidence validator: a document present ⇒ verified; a source URL only ⇒
  probable; neither ⇒ unknown),
* **Confidence contribution**,
* **Kind** — tender / award / document / entity / buyer / supplier (mirroring the
  evidence-reference kinds already in the engine),
* **Bitemporal stamps** (retrieved-at, valid-at).

### 7.5 Evidence connects everything the mandate requires

Per the objective, Evidence links **Documents, Sources, Indicators, Patterns,
Investigations, and Confidence** into one traceable web:

```
Indicator   —BACKED_BY→   Evidence   —CITES→   Document   —OBTAINED_FROM→  Source
Pattern     —BACKED_BY→   (the union of its indicators' Evidence)
Investigation —USES→      Evidence
Confidence  —COMPUTED_FROM→ Evidence quality (coverage, source tier, corroboration)
```

### 7.6 Corroboration and contradiction `[ONT]` `[ARCH]`

Because Evidence is first-class, two Evidence nodes may **corroborate** (support
the same assertion from independent Sources — feeding `CONF-003`) or
**contradict** (assert incompatible facts). Contradiction is modelled explicitly
as a relationship between Evidence nodes, so an investigation can surface *"Source
A says value X, Source B says value Y"* rather than silently picking one.

### 7.7 Evidence immutability

`[ARCH]` Evidence is never edited. New knowledge = new Evidence. A retracted
source produces a *retraction assertion*, not a deletion — the audit trail of
what was once believed is preserved.

---

## Chapter 8 — Investigation Ontology

An **Investigation** is the analytical unit of work: a bounded, provenanced
inquiry into a subject. It is strictly separated from the domain reality it
examines. `[ARCH]`

### 8.1 The investigation spine

```
Investigation
  ├─ ANALYZES →        Subject (an Agent or a ContractingProcess)
  ├─ SCOPES →          a set of Entities, a time window, a jurisdiction
  ├─ GATHERS →         Evidence (Ch.7)
  ├─ SURFACES →        RiskIndicators (Ch.9)
  ├─ COMPOSES →        RiskPatterns  (Ch.9)
  ├─ CONCLUDES_IN →    Findings
  ├─ RECOMMENDS →      Recommendations (Ch.9)
  └─ PRODUCES →        Report
```

### 8.2 Investigation as a first-class, replayable record

`[ARCH]` An Investigation node carries: its subject, scope, the ruleset/ontology
version in force (Book II `GOV-003`), the evidence set considered, the analytical
outputs, and bitemporal stamps. Because it references *versions*, an investigation
is **replayable** and **immutable once concluded** — a later inquiry is a new
Investigation, never a mutation.

### 8.3 Finding

`[ARCH]` A **Finding** is an investigator-facing conclusion *about the evidence*,
distinct from a raw Indicator (machine-surfaced) and from a Recommendation
(next action). A Finding is always `GROUNDED_IN` Evidence and always carries the
oversight caveat — it observes, it does not adjudicate.

### 8.4 Continuity across investigations

`[ARCH]` Investigations link to **prior related investigations** (same subject or
shared entities), giving the graph institutional memory: repeated flags on the
same supplier across time are themselves meaningful. This is a relationship
between Investigation nodes, not a merge of them.

### 8.5 The Investigation Planner's semantic hooks

`[ARCH]` The Planner (a future consumer) reads: the Subject's resolved identity
(Ch.5), the available Evidence coverage (Ch.7), and the recommended next actions'
`REQUIRES_EVIDENCE` edges (Ch.9) to decide what to fetch next. The ontology
exposes these as explicit edges so planning is *graph-driven*, not hardcoded.

---

## Chapter 9 — Risk Ontology

This chapter connects Indicators, Patterns, Evidence, Confidence,
Explainability, and Recommendations **semantically** — *without embedding any
mathematics*. The formulas live in Book II; here we model only *what relates to
what*. `[ARCH]`

### 9.1 RiskIndicator (as an ontology node)

An observed integrity signal, `OBSERVED_ON` a domain target (Tender, Award,
Agent, or Buyer–Supplier pair) and `BACKED_BY` Evidence. It references its
**rule identity** (a Book II ID such as `COMP-001`) — the ontology holds the
*occurrence*; Book II holds the *definition*. No score arithmetic appears here;
the node merely records *which* rule fired, *on what*, *with what evidence*.

### 9.2 RiskPattern

A named combination `COMPOSED_OF` ≥2 RiskIndicators (Book II `PAT-*`). The
ontology models the composition and the `ESCALATES` dependency edges (Book II
IDM), but the *severity lattice* that turns them into a verdict is Book II's, not
the ontology's. This separation is deliberate: the graph stays valid even if the
scoring model is later revised.

### 9.3 Confidence (as an ontology relationship)

Confidence is modelled as a `COMPUTED_FROM` relationship between an analytical
node and the **quality of its Evidence** (coverage, source tier, corroboration,
entity-resolution strength). The ontology names the inputs; Book II §5 supplies
the weights. Crucially, the ontology enforces the **risk ⟂ confidence firewall**:
Confidence attaches to Evidence quality, Severity attaches to the pattern lattice
— they are different edges to different subjects and can never be conflated.

### 9.4 Explainability (as a traversable subgraph)

`[ONT]` Explainability is *not* a separate artifact — it **is** a path in the
graph:

```
Verdict → Pattern → Indicator → Evidence → Document → Source
```

Because every one of those is a first-class node with a real edge, an
explanation is produced by *traversing* the graph, never by generating prose from
nothing. This is the ontological guarantee behind Book II §6.

### 9.5 Recommendation

`DERIVED_FROM` a Pattern/Indicator and `REQUIRES_EVIDENCE` of a specified
DocumentType. A Recommendation names a *verifiable next action*, never a
conclusion (Book II §7). The ontology models the derivation edge so that "why was
this recommended?" is answerable by graph traversal, guaranteeing recommendations
are never free-floating LLM inventions.

### 9.6 No mathematics in the ontology — the firewall restated `[ARCH]`

The ontology may say *"Pattern P is composed of Indicators I1, I2 and escalates
I1"*. It may **not** say *"P = 0.7·I1 + 0.3·I2"*. Thresholds, weights, severity
maps, and score projections are Book II parameters referenced by ID. This keeps
the semantic layer stable across a decade of scoring-model evolution.

---

## Chapter 10 — Graph Design Principles

Principles for representing the ontology *as a graph* — still semantic, not
implementational. `[ONT]` `[ARCH]`

### 10.1 Node types

Nodes come from the nine concept classes plus Identifiers and Time (Ch.1.2).
**Every node is typed** by exactly one class, is **provenanced**, and is
**identity-resolved** (Ch.5). Raw mentions and canonical entities are *distinct*
node kinds linked by confidence-bearing identity edges — the graph never silently
fuses two mentions.

### 10.2 Edge types

Edges are the typed predicates of Chapter 3. Edges are **directed** and
**semantically named** (verbs), never generic "related-to" links — a decade-proof
graph must let analytics distinguish `GOVERNED_BY` from `OWNED_BY` from
`SAME_ADDRESS_AS`.

### 10.3 Edge metadata (every edge carries)

`[ARCH]`

| Metadata | Purpose |
|----------|---------|
| **Source** | Which Source/Document asserts this edge (provenance). |
| **Confidence** | How sure we are the edge holds (feeds Book II §5). |
| **Valid-time interval** | When the edge is true in the world. |
| **Assertion-time** | When SENTRY recorded it (bitemporal, Ch.6). |
| **Ruleset/derivation** | For *derived* edges (Indicators/Patterns), the rule ID that produced it. |
| **Status** | asserted / superseded / retracted (append-only lifecycle). |

### 10.4 Observed vs. derived edges

`[ARCH]` A first-class distinction: **observed** edges come from ingested reality
(a tender's buyer); **derived** edges are computed by rules (a `SHARES_DIRECTOR_WITH`
link, an Indicator's `OBSERVED_ON`). Derived edges always name their producing
rule and are recomputable; observed edges are evidence and are immutable. Mixing
them would make it impossible to tell fact from inference.

### 10.5 Temporal edges

Edges are not timeless. A directorship edge exists only within its interval; a
"current owner" query resolves against valid-time. Analytics must always
traverse **as of a time**, defaulting to "now" but supporting any past instant
(Ch.6.4).

### 10.6 Confidence and validity travel together `[ONT]`

No edge is a bare boolean. Every relationship is a *tuple* of (assertion,
provenance, confidence, validity). Graph Analytics (Ch.12) must respect these:
link-prediction and centrality run over confidence-weighted, time-scoped
subgraphs, never over a naive unweighted graph.

### 10.7 Reversibility

`[ARCH]` Because identity and derivation are fallible, every fused identity and
derived edge is **reversible** without data loss (Ch.5.5). The graph is a record
of *beliefs over time*, and beliefs can be corrected without erasing that they
were once held.

---

## Chapter 11 — International Compatibility

The ontology must model India today and any jurisdiction tomorrow **without
redesign**. `[ARCH]` The mechanism: a stable *core ontology* plus
*jurisdiction-specific vocabularies* that extend, never replace, it.

### 11.1 Core vs. jurisdiction profile

`[DOM]` `[ARCH]` The core (Chapters 2–9) is jurisdiction-neutral: every
procurement system has buyers, tenders, awards, suppliers, methods, and
documents. Jurisdiction-specific facts live in **profiles** that bind local
vocabularies onto core concepts:

| Concept | Core (neutral) | India profile `[IN/DOM]` | International profiles `[DOM]` |
|---------|----------------|--------------------------|-------------------------------|
| Company identifier | `CompanyIdentifier` | CIN | company number, LEI, DUNS |
| Person identifier | `PersonIdentifier` | DIN | national director ID |
| Tax identifier | `TaxIdentifier` | GSTIN, PAN | VAT ID, EIN |
| Buyer taxonomy | `GovernmentBody` | Ministry/Dept/PSU/StateAgency/LocalBody | federal agency, sub-national authority |
| Procurement method | `ProcurementMethod` | GFR/GeM method names | WB/ADB/EU/US method names |
| Funding source | `FundingSource` | domestic budget | World Bank loan, ADB grant, EU fund |

### 11.2 Anchor to an internationally recognized data model

`[DOM]` The core spine (ContractingProcess → Tender → Award → Contract →
Implementation; Parties + Roles) is intentionally aligned with the **Open
Contracting Data Standard (OCDS)** — the most widely adopted open procurement
data model — so that World Bank, ADB, EU (TED), US (SAM/FPDS), and UN data map
onto SENTRY's core with a profile, not a rebuild. Beneficial-ownership modelling
aligns with **FATF/Open Ownership** concepts. These are cited as domain
standards, **not** asserted as legal obligations on any party.

### 11.3 Supported jurisdictions at v1.0

`[DOM]` India, World Bank, ADB, UN Procurement, EU Procurement, US Federal
Procurement — each as a *profile* over the shared core. Adding a country is
adding a profile (identifier schemes, buyer taxonomy, method vocabulary, funding
sources, threshold bindings to Book II `JUR-*`/`THR-*`) with **zero change to the
core ontology**. That is the extensibility test.

### 11.4 Currency and value comparability

`[DOM]` `[ARCH]` Monetary values are always a (amount, currency, as-of-date)
triple; cross-jurisdiction comparison resolves through an FX-rate node at the
value's valid-time. The ontology never stores a bare number as if currency-free.

### 11.5 Multilingual and transliteration support

`[ARCH]` Names and aliases (Ch.5.3) are language-tagged; a canonical entity may
carry names in multiple scripts. Identity resolution is transliteration-aware so
the same supplier in different scripts resolves to one canonical identity.

---

## Chapter 12 — Future Compatibility

How this ontology enables the platform's next decade — by construction, not
retrofit. `[ARCH]`

### 12.1 Knowledge Graph V2

Every chapter of this Book *is* the KG V2 blueprint: typed nodes (Ch.2, 10.1),
verb edges with metadata (Ch.3, 10.2–3), identity resolution (Ch.5), bitemporal
history (Ch.6), and evidence provenance (Ch.7). An engineer can build KG V2
directly from these definitions because it fixes *every* node type, edge type,
constraint, and metadata field the graph requires — while deliberately omitting
storage/query choices so the semantics outlive any technology.

### 12.2 Recommendation Engine

Recommendations are `DERIVED_FROM` patterns and `REQUIRE_EVIDENCE` of document
types (Ch.9.5). Because these are explicit edges, recommendations are generated
by graph traversal and are always explainable and evidence-bound — never
model-hallucinated.

### 12.3 Graph Analytics & Network Analysis

`[ONT]` The confidence-weighted, time-scoped, semantically-typed graph (Ch.10.6)
is the substrate for: **centrality** (which buyers/suppliers are structurally
dominant), **community detection** (clusters of interlinked firms — related-party
rings), **path analysis** (ownership chains from supplier to beneficial owner),
and **bipartite buyer–supplier concentration** analysis. The ontology guarantees
these run over meaningful, provenanced edges rather than noise.

### 12.4 Link Prediction

`[ARCH]` Because observed and derived edges are distinguished (Ch.10.4) and carry
confidence, link prediction can *propose* hidden relationships (e.g. an
unrecorded common owner) as **candidate derived edges** with low confidence and a
"predicted" status — surfaced for investigation, never asserted as fact. This
respects the open-world and provenance principles.

### 12.5 Future AI systems

`[ARCH]` AI reasoners consume the graph as a **grounded evidence context**: they
narrate paths (Ch.9.4), never invent nodes. The ontology's reification of
evidence and its explicit provenance are precisely what makes AI output
verifiable — every sentence an AI produces can be checked against an edge. The
ontology is the guardrail that keeps SENTRY "evidence-centric, not an LLM
wrapper."

### 12.6 Extensibility contract `[ARCH]`

Future growth is **additive**: new entity types, new edge predicates, new
jurisdiction profiles, and new indicator/pattern rule-references extend the
ontology without breaking existing nodes. The nine disjoint concept classes
(Ch.1.2), the identity model (Ch.5), and the bitemporal/provenance metadata
(Ch.10.3) are the **invariant core** — frozen for the decade. Everything else may
grow around them.

---

## Closing — Ratification Notes

* **Relationship to Book I & II.** Book I supplies the philosophy, evidence
  hierarchy, and indicator *definitions*; Book II supplies the *rules,
  thresholds, and mathematics* (with immutable IDs); Book III supplies the
  *nouns, verbs, identity, time, and provenance* they all operate on. The three
  Books are mutually consistent: Book II §12 (Ontology Mapping) is the seam, and
  every `[ID]` referenced here (`COMP-*`, `PAT-*`, `CONF-*`, `JUR-*`, `THR-*`,
  `FP-*`, `GOV-*`) is defined there.
* **What this Book deliberately excludes.** No storage engine, no query language,
  no service boundaries, no code — by design, so the semantics outlive every
  implementation.
* **Freeze criteria.** The nine concept classes, the Agent/Role split, first-class
  Events and Evidence, bitemporal history, explicit revisable identity, and
  provenance-on-every-edge are the constitutional invariants. They may be
  *extended* under an ontology-governance process mirroring Book II §13, but not
  contradicted.

*End of Book III — The Semantic Constitution. Once frozen, amended only by
ontology governance; extensions are additive and versioned.*
```
