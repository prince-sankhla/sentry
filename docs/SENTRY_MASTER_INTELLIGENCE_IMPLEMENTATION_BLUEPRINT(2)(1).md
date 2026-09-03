# SENTRY --- Master Intelligence & Implementation Blueprint

## Purpose

This document is the implementation companion to the SENTRY master Excel
roadmap.

The Excel defines **what SENTRY should know and detect**.\
This document defines **how the engineering team/Claude should turn that
design into a working system**.

SENTRY must not become a simple "red-flag score generator".

The target system is:

> **Evidence-backed procurement investigation intelligence.**

It should understand a tender in context: its buyer, suppliers, bidders,
historical procurement behaviour, relationships, benchmarks, procurement
rules, official records, credible external reporting, and longitudinal
patterns.

------------------------------------------------------------------------

# 1. Core Product Principle

SENTRY should answer:

> **"What is unusual here, why is it unusual in this context, what
> evidence supports that observation, what legitimate explanations
> exist, and what should an investigator inspect next?"**

It should NOT answer:

> "This company is corrupt."

Risk signals are investigative prioritization, not a legal or factual
finding of wrongdoing.

Every important output must separate:

1.  **Observed fact**
2.  **Derived statistic**
3.  **Pattern/inference**
4.  **External context**
5.  **Alternative explanation**
6.  **Evidence quality**
7.  **Confidence**
8.  **Human-review status**

------------------------------------------------------------------------

# 2. End-to-End Architecture

``` text
PUBLIC / AUTHORIZED SOURCES
        |
        v
DATA INGESTION
        |
        +---- Procurement records
        +---- Rules / manuals
        +---- Official cases / debarments
        +---- Corporate/public entity records
        +---- News / public reporting
        |
        v
NORMALIZATION
        |
        v
ENTITY RESOLUTION
        |
        v
CANONICAL PROCUREMENT DATA
        |
        +-------------------+
        |                   |
        v                   v
BENCHMARK ENGINE       ECOSYSTEM GRAPH
        |                   |
        +---------+---------+
                  |
                  v
            PATTERN ENGINE
                  |
                  v
        EVIDENCE + PROVENANCE
                  |
                  v
       ALTERNATIVE EXPLANATION
                  |
                  v
        SIGNAL CONVERGENCE
                  |
                  v
        RISK PRIORITIZATION
                  |
                  v
        INVESTIGATION BRIEF
                  |
                  v
          HUMAN REVIEW
```

------------------------------------------------------------------------

# 3. What SENTRY Must Understand

## 3.1 Tender

For every tender, build a canonical profile:

-   tender ID
-   buyer
-   title
-   category
-   procurement method
-   estimated value
-   publication date
-   deadline
-   award date
-   status
-   geography
-   qualification criteria
-   technical specifications
-   corrigenda
-   bid count
-   responsive bid count
-   award supplier
-   award value
-   source URLs
-   source snapshots
-   evidence completeness

### Derived tender features

-   submission duration
-   award/estimate ratio
-   bidder count
-   responsive bidder count
-   amendment count
-   deadline extensions
-   lifecycle completeness
-   comparable-tender percentile
-   buyer baseline deviation
-   category baseline deviation

------------------------------------------------------------------------

# 4. Supplier "Kundali"

Every supplier should have a longitudinal profile.

## Facts

-   legal name
-   public registration identifiers
-   aliases
-   procurement categories
-   geography
-   historical tenders
-   wins
-   losses
-   participation
-   award values
-   buyers served
-   tender sizes
-   procurement methods
-   publicly documented eligibility/debarment status where available

## Derived behaviour

-   win rate
-   participation rate
-   buyer concentration
-   category concentration
-   geographic concentration
-   value distribution
-   repeat-winner frequency
-   winner streaks
-   bid-price behaviour
-   competitor participation behaviour
-   co-bidding relationships
-   temporal behaviour changes

## Important

Do not convert:

`high win rate -> suspicious`

Instead:

`high win rate -> concentration signal -> compare against appropriate market population -> inspect context -> seek corroborating evidence`

------------------------------------------------------------------------

# 5. Buyer "Kundali"

For each procuring entity:

-   tender volume
-   categories
-   average tender value
-   bidder distribution
-   supplier concentration
-   repeat suppliers
-   procurement-method distribution
-   submission-window distribution
-   award/estimate distribution
-   cancellation/re-tender frequency
-   corrigendum patterns
-   historical benchmark

The buyer should have its own baseline.

A supplier may have a 70% win rate with Buyer A but only 10% across the
broader market. Those are different signals.

------------------------------------------------------------------------

# 6. Bidder Behaviour

Where bid-level data is available, preserve every bid as a first-class
object.

Fields:

-   bid ID
-   tender ID
-   supplier ID
-   submission timestamp
-   bid amount
-   rank
-   responsive/non-responsive
-   withdrawal status
-   qualification result
-   document references

Derived features:

-   normalized bid price
-   winner-to-second spread
-   bid dispersion
-   repeated pairwise price gaps
-   repeated ranking
-   submission-time clustering
-   participation changes
-   bidder-pair behaviour
-   longitudinal price behaviour

------------------------------------------------------------------------

# 7. Ecosystem Graph

SENTRY should represent procurement as a graph.

## Nodes

-   Tender
-   Buyer
-   Supplier
-   Bid
-   Organization
-   Market/category
-   Document
-   Official case
-   News event
-   Person/officer only where necessary, public, lawful, and relevant

## Edges

-   BUYER -\> ISSUED -\> TENDER
-   SUPPLIER -\> BID_ON -\> TENDER
-   SUPPLIER -\> WON -\> TENDER
-   SUPPLIER -\> LOST -\> TENDER
-   SUPPLIER -\> CO_BIDDED_WITH -\> SUPPLIER
-   BUYER -\> AWARDED_TO -\> SUPPLIER
-   ENTITY -\> RELATED_TO -\> ENTITY
-   CASE -\> INVOLVES -\> ENTITY
-   NEWS -\> MENTIONS -\> ENTITY
-   NEWS -\> RELATES_TO -\> TENDER
-   DOCUMENT -\> SUPPORTS -\> CLAIM
-   TENDER -\> BELONGS_TO -\> CATEGORY

Every edge should have:

-   source
-   observed date
-   source URL
-   evidence ID
-   confidence
-   relationship type

Relationship is not proof of misconduct.

------------------------------------------------------------------------

# 8. Pattern Intelligence

The system should detect patterns across:

## Competition

-   single/low bidder
-   declining competition
-   repeated low participation

## Winner behaviour

-   repeated winner
-   winner concentration
-   winner rotation
-   winner streaks

## Pricing

-   repeated price gaps
-   suspiciously similar prices
-   identical prices
-   unusual bid spreads
-   repeated losing-bid structures
-   award/estimate anomalies

## Participation

-   withdrawal patterns
-   competitor-conditioned non-participation
-   supplier entry/exit
-   sudden participation changes

## Network

-   repeated supplier pairs
-   dense co-bidding clusters
-   buyer-supplier concentration
-   recurring subgraphs

## Geography / market

-   geographic allocation
-   category allocation
-   market-share shifts
-   supplier-region exclusivity

## Tender design

-   restrictive qualification
-   unusual eligibility thresholds
-   unusual specification patterns
-   repeated template structures
-   targeted specification similarity

## Timing

-   unusually short submission period
-   repeated deadline changes
-   tender clustering
-   synchronized submission timestamps
-   behaviour change points

## Documents

-   document similarity
-   rare repeated typo
-   formatting fingerprint
-   metadata similarity
-   arithmetic/rounding fingerprints

## Meta-patterns

-   evidence convergence
-   alternative explanations
-   data-quality uncertainty

------------------------------------------------------------------------

# 9. Human-Like Investigation Model

A real investigator does not stop at the first anomaly.

SENTRY should follow:

``` text
DETECT
  |
CONTEXTUALIZE
  |
CONNECT
  |
COMPARE
  |
CHALLENGE
  |
CORROBORATE
  |
VERIFY
  |
PRIORITIZE
  |
HUMAN DECISION
```

## Detect

Something differs from normal.

## Contextualize

Is it actually unusual for this buyer/category/geography/value/method?

## Connect

Which entities and previous tenders are related?

## Compare

What happened in comparable procurement?

## Challenge

What legitimate explanation could produce the same observation?

## Corroborate

Do independent signal families agree?

## Verify

Can the investigator open the original source?

## Prioritize

Is the evidence strong enough to deserve human attention?

## Human decision

The system does not adjudicate guilt.

------------------------------------------------------------------------

# 10. Benchmark Engine

Never use arbitrary global thresholds when a contextual benchmark is
possible.

Benchmark dimensions may include:

-   procurement category
-   buyer
-   geography
-   procurement method
-   tender value band
-   time period
-   supplier market
-   project type

Use:

-   sample size
-   median
-   P25/P75
-   IQR
-   percentile
-   robust deviation
-   historical trend
-   buyer baseline
-   category baseline

Every benchmark must store:

``` text
benchmark_id
population_definition
dimensions
sample_size
calculation_method
baseline
created_at
refresh_at
source_query/version
```

Never compare a highly specialized procurement with an unrelated
commodity tender.

------------------------------------------------------------------------

# 11. News Intelligence

News is **contextual evidence**, not an automatic risk score.

## 11.1 What to search

For a tender:

### Tender queries

-   exact tender title
-   tender ID
-   project name
-   buyer + project
-   buyer + tender ID
-   project + procurement category

### Supplier queries

-   exact legal supplier name
-   supplier + tender
-   supplier + buyer
-   supplier + contract
-   supplier + debarment
-   supplier + CCI
-   supplier + court
-   supplier + investigation
-   supplier + project

### Buyer queries

-   buyer + procurement
-   buyer + tender
-   buyer + project
-   buyer + audit
-   buyer + investigation

### Relationship queries

-   supplier A + supplier B
-   supplier A + supplier B + tender
-   supplier A + supplier B + contract

Do not search only the current tender. Search a time window around the
tender and relevant historical periods.

------------------------------------------------------------------------

# 12. News Retrieval Architecture

Do not make the risk engine itself scrape the web.

Use a separate:

``` text
News Discovery Layer
        |
        v
Candidate Articles
        |
        v
Deduplication
        |
        v
Entity/Tender Matching
        |
        v
Relevance Classification
        |
        v
Source Quality Classification
        |
        v
Evidence Store
```

## Discovery sources

Prefer:

1.  official government/authority publications
2.  official court/CCI/DoE notices
3.  established publishers
4.  reputable sector publications
5.  search-engine discovery results
6.  other public sources only when their reliability and access rights
    are clear

Search engines are a discovery mechanism, not the source of truth.

For a production system, use a supported search/news API or licensed
provider where appropriate. Do not build a scraper that attempts to
bypass publisher controls.

------------------------------------------------------------------------

# 13. News Article Object

Store:

``` text
article_id
canonical_url
publisher
title
publication_date
retrieved_at
author_if_available
language
snippet
content_available
content_source_type
matched_entities
matched_tenders
event_type
relevance_score
source_quality
corroboration_count
status
```

If the full article cannot legally or technically be stored, store the
metadata and a short permitted excerpt/summary with the original URL.

Do not copy entire copyrighted articles into SENTRY.

------------------------------------------------------------------------

# 14. News Relevance Pipeline

For each discovered article:

### Step 1 --- Entity matching

Does it actually refer to the same supplier/buyer/project?

### Step 2 --- Temporal relevance

Is it before, during, or after the tender?

### Step 3 --- Semantic relevance

Does the article discuss:

-   procurement
-   contract
-   project
-   enforcement
-   competition
-   litigation
-   audit
-   debarment
-   performance
-   dispute
-   investigation
-   financial/operational event

### Step 4 --- Source quality

Classify:

``` text
A = official / primary
B = established credible publisher
C = secondary / uncertain
D = unreliable / unusable
```

### Step 5 --- Corroboration

If multiple independent credible sources report the same event, connect
them to one event rather than counting them as many independent risk
signals.

### Step 6 --- Status

Every case/event must carry:

-   allegation
-   investigation
-   charge
-   proceeding
-   judgment/order
-   dismissed
-   acquitted
-   settled
-   resolved
-   unknown

Never collapse these into "bad history".

------------------------------------------------------------------------

# 15. News Must Never Directly Create High Risk

Bad design:

``` text
News article mentions "investigation"
        ↓
Risk +30
```

Correct design:

``` text
Article discovered
      ↓
Entity matched
      ↓
Source quality checked
      ↓
Event extracted
      ↓
Official source searched for corroboration
      ↓
Status identified
      ↓
Investigator context created
```

Only an independently verified, relevant fact may participate in a rule
that explicitly requires it.

------------------------------------------------------------------------

# 16. Official Case / Debarment Intelligence

For official records store:

-   authority
-   case/order ID
-   entity
-   date
-   status
-   outcome
-   scope
-   effective date
-   expiry date if applicable
-   source URL
-   evidence snapshot

Important:

``` text
Past case != current wrongdoing
Allegation != finding
Expired debarment != active debarment
Unrelated case != relevant evidence
```

An active official eligibility restriction that applies on the tender
date is fundamentally different from a historical news allegation.

------------------------------------------------------------------------

# 17. Entity Resolution

Use this order:

``` text
1. Exact authoritative identifier
2. Exact normalized legal name
3. Known aliases
4. Public organization identifiers
5. Supporting address/contact signals
6. Official corporate relationships
7. Historical behaviour
8. Human review for ambiguity
```

Never merge entities purely because their names are similar.

Every merge should have an auditable resolution record.

------------------------------------------------------------------------

# 18. Risk vs Context

## May contribute to risk

-   contextualized competition anomalies
-   validated pricing anomalies
-   repeated winner/rotation patterns
-   validated participation patterns
-   validated network patterns
-   applicable procurement-rule deviations
-   active official eligibility/debarment status
-   evidence convergence

## Context only by default

-   news articles
-   historical cases
-   court proceedings without relevant final status
-   shared addresses
-   shared directors
-   supplier reputation
-   generic media sentiment

## Never treat as a positive risk signal

-   missing data
-   incomplete publication
-   AI-generated speculation
-   entity-resolution uncertainty

Missing data should generally reduce confidence.

------------------------------------------------------------------------

# 19. Evidence Architecture

Every important claim should resolve to evidence.

Minimum:

``` text
evidence_id
source_type
source_url
retrieved_at
snapshot_id
claim
entity/tender reference
source_quality
```

Prefer:

``` text
document/page/section
table/row
calculation
query version
hash
```

The investigator should be able to answer:

> "Why did SENTRY say this?"

with a traceable chain.

------------------------------------------------------------------------

# 20. Risk Calculation

Do not begin with an arbitrary weighted sum.

First calculate individual signals:

``` text
Signal
Context
Benchmark deviation
Evidence quality
Confidence
```

Then combine signals carefully.

Example:

``` text
Signal A: low competition
Signal B: repeated winner
Signal C: repeated price gap
Signal D: competitor non-participation
```

If A/B/C/D are mathematically correlated, do not count them as four
independent pieces of evidence.

Use an evidence-diversity concept:

``` text
Competition
Pricing
Participation
Network
Document
External/Official Context
```

Independent signal families should carry more evidentiary value than
multiple variants of the same measurement.

------------------------------------------------------------------------

# 21. Alternative Explanation Engine

Every high-priority pattern should test possible legitimate
explanations.

Examples:

### Low bidder count

Possible explanations:

-   specialized market
-   remote geography
-   low supplier universe
-   emergency procurement
-   highly technical requirement

### Winner concentration

Possible explanations:

-   framework contract
-   specialized supplier
-   regional monopoly
-   legitimate qualification advantage

### Short tender period

Possible explanations:

-   emergency procurement
-   applicable exception
-   extension/corrigendum
-   specific procurement method

### Similar bid prices

Possible explanations:

-   standardized catalog prices
-   regulated pricing
-   common industry price list
-   identical official schedule rates

The system should record:

``` text
Pattern
+
Alternative explanation
+
Evidence for explanation
+
Residual unexplained anomaly
```

------------------------------------------------------------------------

# 22. AI Layer

AI should operate on structured evidence.

### AI may:

-   summarize the tender
-   connect related historical tenders
-   explain detected patterns
-   compare evidence
-   retrieve relevant supporting documents
-   generate investigation timelines
-   identify missing evidence
-   propose follow-up questions
-   summarize news context
-   explain why a benchmark is unusual

### AI must not:

-   invent evidence
-   invent sources
-   declare guilt
-   turn allegations into facts
-   silently merge entities
-   create arbitrary thresholds
-   replace deterministic calculations
-   use news sentiment as proof
-   hide uncertainty

Every generated statement should be grounded in stored evidence or
clearly marked as an inference.

------------------------------------------------------------------------

# 23. Investigation Brief

A final SENTRY investigation view should look like:

``` text
CASE
Tender: XXXXX
Buyer: XXXXX
Supplier: XXXXX

EXECUTIVE SIGNAL
--------------------------------
Priority: High
Confidence: 0.78
Evidence quality: Strong

WHY IT WAS FLAGGED
--------------------------------
1. Competition anomaly
2. Repeated supplier concentration
3. Repeated price-gap pattern

BENCHMARK
--------------------------------
Comparable tenders: 428
Median bidders: 6
Current responsive bidders: 1

PATTERN
--------------------------------
Supplier A won 15/18 comparable tenders.
Supplier B participated in 16 but lost 15.

RELATIONSHIPS
--------------------------------
A and B appeared together in 18 tenders.

EXTERNAL CONTEXT
--------------------------------
2 credible articles
1 official record
Status explicitly shown

ALTERNATIVE EXPLANATIONS
--------------------------------
Specialized supplier market: partially supported
Regional restriction: weak evidence

EVIDENCE
--------------------------------
[Source 1]
[Source 2]
[Source 3]

DATA GAPS
--------------------------------
No complete losing-bid documents for 4 tenders.

RECOMMENDED REVIEW
--------------------------------
Inspect qualification criteria and bid documents.
```

------------------------------------------------------------------------

# 24. P0 Implementation Order

Do NOT implement everything simultaneously.

## P0.1 --- Canonical procurement model

Tender → Bid → Award → Buyer → Supplier → Evidence

## P0.2 --- Entity resolution

Stable IDs and provenance.

## P0.3 --- Historical benchmark engine

Comparable populations and minimum sample thresholds.

## P0.4 --- Core patterns

Start with:

1.  single/low bidder
2.  concentration/repeated winner
3.  winner rotation
4.  repeated price gap
5.  bid similarity
6.  award/estimate anomaly
7.  bid spread
8.  applicable timing anomaly
9.  evidence completeness

## P0.5 --- Alternative explanations

Before high-priority scoring.

## P0.6 --- Evidence/audit trail

Every signal must be explainable.

## P0.7 --- Ecosystem graph

Buyer/supplier/tender relationships.

## P0.8 --- Investigation brief

Only after the underlying evidence pipeline works.

------------------------------------------------------------------------

# 25. P1 Implementation

After P0 is validated:

-   geographic allocation
-   participation suppression
-   co-bidding networks
-   document similarity
-   timestamp patterns
-   corrigendum patterns
-   bidder entry/exit
-   change-point detection
-   richer buyer/supplier profiles
-   official case/debarment integration
-   news intelligence

------------------------------------------------------------------------

# 26. P2 Implementation

Later:

-   post-award relationship analysis
-   subcontract/JV transitions
-   advanced document fingerprints
-   market-share shocks
-   tender-template evolution
-   richer external event graph
-   calibrated machine-learning models

------------------------------------------------------------------------

# 27. Validation Requirements

Before claiming a pattern works:

## Synthetic tests

Create controlled examples for:

-   winner rotation
-   geographic allocation
-   repeated price gaps
-   participation suppression
-   document similarity
-   missing data
-   legitimate specialized procurement

## Historical backtesting

Run the detector against historical procurement data.

Measure:

-   precision
-   recall where labels exist
-   false-positive rate
-   stability across categories
-   stability across buyers
-   sensitivity to sample size

## Human review

Have a reviewer inspect:

-   top cases
-   false positives
-   false negatives
-   evidence quality
-   explanation quality

------------------------------------------------------------------------

# 28. Source and Web Compliance

News and external data must be collected through permitted access
methods.

Use:

-   official APIs
-   licensed data providers
-   public pages where access is permitted
-   search APIs/providers
-   RSS/feeds where offered
-   official downloadable datasets

Respect:

-   robots.txt
-   publisher terms
-   rate limits
-   copyright
-   access controls
-   authentication boundaries

Never bypass:

-   login walls
-   CAPTCHAs
-   anti-bot controls
-   paywalls
-   technical restrictions

Store links and metadata when full content cannot be stored legally.

------------------------------------------------------------------------

# 29. Recommended News Search Strategy

For each entity, create query templates.

Example:

``` text
"<supplier legal name>" tender
"<supplier legal name>" procurement
"<supplier legal name>" contract
"<supplier legal name>" debarred
"<supplier legal name>" CCI
"<supplier legal name>" court
"<supplier legal name>" investigation

"<buyer>" tender "<project>"
"<tender ID>"
"<tender title>"
"<project name>" procurement
```

For each query:

``` text
SEARCH
  ↓
COLLECT candidates
  ↓
DEDUPLICATE
  ↓
MATCH entity
  ↓
MATCH tender
  ↓
CLASSIFY event
  ↓
CLASSIFY source quality
  ↓
CHECK official corroboration
  ↓
STORE evidence
```

Do not run thousands of uncontrolled searches for every tender.

Use a tiered strategy:

### Tier 1

Official sources.

### Tier 2

High-quality targeted news search.

### Tier 3

Broader discovery only when investigation priority justifies it.

This keeps the system cheaper, faster and more defensible.

------------------------------------------------------------------------

# 30. What Claude Should Build

When this document and the Excel are provided to Claude with the
repository, Claude should:

1.  inspect the existing repository before changing code
2.  map existing modules to this blueprint
3.  preserve working functionality
4.  identify duplicate/obsolete detectors
5.  implement P0 first
6.  add schemas/models before complex analytics
7.  create deterministic tests
8.  create synthetic pattern fixtures
9.  add provenance to every external fact
10. keep AI outside the source-of-truth calculation path
11. expose confidence and evidence gaps
12. never invent data
13. never silently change risk thresholds
14. document every new module

------------------------------------------------------------------------

# 31. Definition of Done

SENTRY is not "done" because the dashboard looks good.

P0 is done when:

-   a tender can be ingested
-   entities are resolved
-   historical comparable tenders are retrieved
-   benchmarks are reproducible
-   core patterns are calculated
-   legitimate explanations are checked
-   evidence is attached
-   confidence is calculated
-   related ecosystem entities are shown
-   the investigation timeline is generated
-   every important conclusion is traceable
-   missing data is explicit
-   tests cover known patterns and legitimate counterexamples

------------------------------------------------------------------------

# 32. Product North Star

The final SENTRY experience should feel like:

> **"Give me one tender and I will reconstruct the relevant procurement
> ecosystem around it, identify what is statistically or procedurally
> unusual, connect it to historical behaviour and relationships, show
> the evidence, challenge my own hypothesis with legitimate
> explanations, and tell a human investigator exactly what deserves
> attention next."**

Not:

> "Here is a red score of 82/100."

That distinction is the core of SENTRY.
