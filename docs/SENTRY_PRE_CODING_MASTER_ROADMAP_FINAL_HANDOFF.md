# DOCUMENT CONTROL — HOW CLAUDE MUST USE THE SENTRY FILES

## Purpose

This document is the **WHAT + WHY** specification for SENTRY.

It must be read together with:

**`SENTRY_MASTER_INTELLIGENCE_IMPLEMENTATION_BLUEPRINT(2).md`**

which is the **HOW** / implementation blueprint.

The **existing SENTRY repository is the current implementation reality**. Documentation must never be assumed to exactly match the code.

---

## 1. Document Roles

### Document 1 — This file

**Role:** WHAT + WHY

Use this document for:

- procurement rules
- red flags
- benchmarks
- pattern library
- entities
- relationships
- ecosystem model
- P0/P1/P2 priorities
- detector requirements
- evidence requirements
- research findings
- source authority
- what should and should not contribute to risk

Do **not** treat international methodologies, academic research, or contextual evidence as Indian law merely because they appear in this document.

### Document 2 — `SENTRY_MASTER_INTELLIGENCE_IMPLEMENTATION_BLUEPRINT(2).md`

**Role:** HOW

Use it for:

- repository integration
- architecture
- implementation approach
- module/data flow
- evidence pipeline
- news pipeline
- entity resolution
- risk engine
- validation
- testing
- implementation sequence
- Definition of Done

### Existing SENTRY Repository

**Role:** CURRENT REALITY

Claude must inspect the repository before making implementation decisions.

Do not assume that a documented feature already exists, or that a documented architecture exactly matches the current code.

---

## 2. Mandatory Work Order

Claude must follow this sequence:

1. Read this document completely.
2. Read `SENTRY_MASTER_INTELLIGENCE_IMPLEMENTATION_BLUEPRINT(2).md` completely.
3. Inspect the existing SENTRY repository and its current architecture.
4. Map documentation requirements against the existing implementation.
5. Produce a gap report:
   - already implemented
   - partially implemented
   - missing
   - obsolete/conflicting code
   - data-source gaps
   - dependency/library gaps
   - test/validation gaps
6. Produce a proposed implementation sequence.
7. **Do not modify code during the initial audit.**
8. After the implementation plan is approved, implement P0 first.
9. Add deterministic tests and preserve evidence/provenance.
10. Implement P1 only after P0 is validated.
11. Implement P2/research features only after the necessary data and validation exist.

---

## 3. Source Authority Hierarchy

Use this hierarchy when interpreting evidence:

1. **Indian authoritative procurement sources**
   - GFR
   - Department of Expenditure manuals
   - applicable government procurement rules/guidance
   - CPPP/eProcure records
   - GeM rules/data where applicable
   - CCI official material/orders where applicable
   - official debarment/blacklisting records

2. **International methodologies**
   - OECD
   - Open Contracting Partnership
   - World Bank
   - relevant EU/UN methodologies

3. **Academic / research evidence**

4. **News and other external contextual sources**

A lower-level source must not silently be promoted into an authoritative rule.

---

## 4. Non-Negotiable Engineering Rules

- Do not invent procurement rules.
- Do not invent arbitrary risk thresholds.
- Do not treat a single red flag as proof of wrongdoing.
- Missing data must not automatically increase risk.
- News allegations are contextual evidence, not proof.
- AI inference is not the source of truth for deterministic risk calculations.
- Preserve source provenance for important findings.
- Preserve existing working functionality unless there is a documented reason to change it.
- Prefer explainable deterministic detectors before ML.
- Keep authoritative rules, analytical indicators, benchmarks, contextual evidence, and AI inference distinguishable in the data model and UI.
- Every detector should expose enough context for an investigator to understand why it fired.
- `INSUFFICIENT_DATA` / uncertainty should remain a valid outcome where evidence is incomplete.

---

## 5. SENTRY's Intended Investigation Flow

The implementation should support the investigator journey:

**Detect → Contextualize → Connect → Compare → Challenge → Corroborate → Verify → Prioritize → Human Decision**

The objective is not merely to produce a red badge or a score. The objective is to produce an evidence-backed investigation trail that a human reviewer can challenge and verify.

---

## 6. Final Handoff Model

The two planning documents have deliberately separate responsibilities:

```text
DOCUMENT 1
WHAT + WHY
Rules / Patterns / Benchmarks / Ecosystem / Research
                         │
                         ▼
DOCUMENT 2
HOW
Architecture / Implementation / Validation
                         │
                         ▼
EXISTING REPOSITORY
Current implementation
                         │
                         ▼
AUDIT → GAP REPORT → IMPLEMENTATION PLAN → CODE
```

Do not skip the audit stage.


---

# SENTRY --- PRE-CODING MASTER ROADMAP (COMPLETE EXCEL → MARKDOWN)

> Exact structural transcription of the workbook. Every worksheet,
> column, row, and cell value is preserved in Markdown table form. No
> row intentionally omitted.

## Sheet: Master Status

  -----------------------------------------------------------------------------------------------------------------------
  Layer             Status            Current State                                                    Next Action
  ----------------- ----------------- ---------------------------------------------------------------- ------------------
  Phase 1 Rule      COMPLETE          Authoritative sources + applicability/exceptions/evidence fields Maintain/version
  Registry                                                                                             

  Phase 1 Red-Flag  COMPLETE          Indicator logic, fields, false positives, confidence             Validate against
  Registry                                                                                             real data

  Phase 1 Benchmark COMPLETE          Peer tiers/statistics/sample policies                            Calibrate on
  Registry                                                                                             validation corpus

  Detector Output   COMPLETE          Signal→Context→Benchmark→Evidence→Confidence→Risk→Explanation    Implement schema
  Contract                                                                                             

  TenderShield      COMPLETE          Five functions mapped; 3 core now, 2 later                       Implement selected
  parity plan                                                                                          MVP

  Pre-coding        COMPLETE          Keep/change/add/remove decisions documented                      Create code-task
  architecture                                                                                         prompts for Claude

  Phase 2           NOT STARTED       No code changes in this planning step                            Proceed only after
  implementation                                                                                       plan review

  Pattern           ADDED             Human-style contextual/longitudinal/network pattern model now    Implement pattern
  Intelligence                        specified                                                        feature layer
                                                                                                       after core P0
                                                                                                       detectors

  Candidate Pattern COMPLETE          36 candidate patterns cross-mapped to source families and        Convert P0
  Library                             P0/P1/P2                                                         patterns into
                                                                                                       formal algorithm
                                                                                                       specs before
                                                                                                       coding

  Ecosystem         DESIGN COMPLETE   Tender→buyer→supplier→relationship→case→news→market→post-award   Formalize P0 data
  Intelligence                        ecosystem model added                                            contracts and
                                                                                                       source adapters
                                                                                                       before coding

  Ecosystem Data    COMPLETE          P0/P1/P2 fields, entity resolution, graph nodes/edges,           Next: formal P0
  Model                               risk-vs-context boundaries and P0 data contracts defined         detector formulas
                                                                                                       and implementation
                                                                                                       task map

  P0 Detector +     COMPLETE          Exact P0 detector contracts, implementation sequence, acceptance Pre-coding
  Implementation                      tests, and output contract added                                 specification is
  Specification                                                                                        now locked;
                                                                                                       implementation can
                                                                                                       proceed against
                                                                                                       Excel + MD + repo
  -----------------------------------------------------------------------------------------------------------------------

## Sheet: Rule Registry

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Rule ID      Rule / Signal            Type         Authority /   Source Document   Source Reference         Applicability                   Machine Check       Required Data         Context / Exception       Evidence Required           Output                Severity            Implementation   Source URL                                                                                                                                                      Last
                                                     Methodology                                                                                                                        Checks                                                                                          Priority                                                                                                                                                                         Verified
  ------------ ------------------------ ------------ ------------- ----------------- ------------------------ ------------------------------- ------------------- --------------------- ------------------------- --------------------------- --------------------- ------------------- ---------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------- ------------
  COMP-001     Single / low competition Rule + Red   Department of Manual for        Competition / single-bid Open competitive procurement;   Partial             bid count; responsive Check publicity, adequate Tender notice; bid records; SUPPORTED / NOT       Context-dependent   P0               https://doe.gov.in/files/circulars_document/Manual_Goods_2024.pdf                                                                                               2026-08-15
               signal                   Flag         Expenditure   Procurement of    guidance                 adapt by procurement type                           bid count;            submission time,          evaluation/award records    SUPPORTED /                                                                                                                                                                                                                
                                                                   Goods, 2nd Ed.,                                                                                procurement method;   restrictive qualification                             INSUFFICIENT_DATA                                                                                                                                                                                                          
                                                                   2024                                                                                           category; value;      criteria,                                                                                                                                                                                                                                                                        
                                                                                                                                                                  dates                 specialized/emergency                                                                                                                                                                                                                                                            
                                                                                                                                                                                        context, price                                                                                                                                                                                                                                                                   
                                                                                                                                                                                        reasonableness                                                                                                                                                                                                                                                                   

  COMP-002     Insufficient tender      Rule + Red   Department of Manual for        Risk/mitigation section  Open tenders                    Yes if              publication date; bid Compare against           Tender notice; publication  FLAG / CLEAR /        Context-dependent   P0               https://doe.gov.in/files/circulars_document/Manual_Goods_2024.pdf                                                                                               2026-08-15
               publicity / short        Flag         Expenditure   Procurement of    on publicity and                                         dates/publication   submission end;       applicable tender         timestamps;                 INSUFFICIENT_DATA                                                                                                                                                                                                          
               submission period                                   Goods, 2nd Ed.,   adequate time                                            data available      tender method;        requirements; identify    approval/extension records                                                                                                                                                                                                                             
                                                                   2024                                                                                           approval/extension    justified shortened                                                                                                                                                                                                                                                              
                                                                                                                                                                  data                  periods                                                                                                                                                                                                                                                                          

  COMP-003     Non-objective / unclear  Rule + Red   Department of Manual for        Risk/mitigation section  Procurement with defined        Partial             tender document;      Human review may be       Tender document and         FLAG / CLEAR /        Context-dependent   P1               https://doe.gov.in/files/circulars_document/Manual_Goods_2024.pdf                                                                                               2026-08-15
               evaluation criteria      Flag         Expenditure   Procurement of    on objective and clearly evaluation criteria                                 evaluation criteria;  required; NLP can detect  amendments                  INSUFFICIENT_DATA                                                                                                                                                                                                          
                                                                   Goods, 2nd Ed.,   stated criteria                                                              qualification         missing/ambiguous                                                                                                                                                                                                                                                                
                                                                   2024                                                                                           criteria              criteria                                                                                                                                                                                                                                                                         

  BID-001      Repeated same winner /   Red Flag     OECD 2025     OECD Guidelines   3.1 Warning signs in     Comparable tenders over time    Yes                 tender IDs; winners;  Must benchmark against    Award records; bidder       ANOMALY / NO_ANOMALY  Context-dependent   P0               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               winner concentration                  Bid-Rigging   for Fighting Bid  bidding patterns                                                             bidder participation; comparable tenders;       participation history       / INSUFFICIENT_DATA                                                                                                                                                                                                        
                                                     Detection     Rigging in Public                                                                              category; geography;  concentration can be                                                                                                                                                                                                                                                             
                                                     List          Procurement (2025                                                                              dates                 legitimate in                                                                                                                                                                                                                                                                    
                                                                   Update)                                                                                                              small/specialized markets                                                                                                                                                                                                                                                        

  BID-002      Bid rotation /           Red Flag     OECD 2025     OECD Guidelines   3.1 Warning signs in     Repeated procurements with      Yes if historical   winner sequence;      Require multiple tenders; Award history; bidder       ANOMALY / NO_ANOMALY  Context-dependent   P1               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               geographic allocation                 Bid-Rigging   for Fighting Bid  bidding patterns         comparable bidders              awards exist        bidder set;           avoid inferring collusion history                     / INSUFFICIENT_DATA                                                                                                                                                                                                        
               pattern                               Detection     Rigging in Public                                                                              geography; category;  from one event                                                                                                                                                                                                                                                                   
                                                     List          Procurement (2025                                                                              dates                                                                                                                                                                                                                                                                                                  
                                                                   Update)                                                                                                                                                                                                                                                                                                                                                                                               

  BID-003      Unexpected / repeated    Red Flag     OECD 2025     OECD Guidelines   3.1 Warning signs in     Tenders with bid-status history Yes if              bid status; bidder;   Check legitimate          Bid submission/status       ANOMALY / NO_ANOMALY  Context-dependent   P1               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               bid withdrawal or                     Bid-Rigging   for Fighting Bid  bidding patterns                                         withdrawal/status   tender; withdrawal    withdrawal reasons where  records                     / INSUFFICIENT_DATA                                                                                                                                                                                                        
               suppression pattern                   Detection     Rigging in Public                                                          data available      time; historical      available                                                                                                                                                                                                                                                                        
                                                     List          Procurement (2025                                                                              participation                                                                                                                                                                                                                                                                                          
                                                                   Update)                                                                                                                                                                                                                                                                                                                                                                                               

  PRICE-001    Identical /              Red Flag     OECD 2025     OECD Guidelines   3.3 Warning signs        Tenders with bidder-level       Yes                 bidder; bid amount;   Normalize                 Bid sheets / BOQ / price    ANOMALY / NO_ANOMALY  Context-dependent   P0               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               near-identical bid                    Bid-Rigging   for Fighting Bid  related to pricing       prices                                              tender; currency;     currency/rounding;        submissions                 / INSUFFICIENT_DATA                                                                                                                                                                                                        
               prices                                Detection     Rigging in Public                                                                              line-item prices if   account for regulated                                                                                                                                                                                                                                                            
                                                     List          Procurement (2025                                                                              available             pricing or identical                                                                                                                                                                                                                                                             
                                                                   Update)                                                                                                              catalog prices                                                                                                                                                                                                                                                                   

  PRICE-002    Suspiciously             Red Flag     OECD 2025     OECD Guidelines   3.3 Warning signs        Repeated tenders with           Yes                 bid amounts across    Requires sufficient       Historical bid records      ANOMALY / NO_ANOMALY  Context-dependent   P1               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               regular/repetitive                    Bid-Rigging   for Fighting Bid  related to pricing       bidder-level prices                                 tenders; bidder       historical sample;                                    / INSUFFICIENT_DATA                                                                                                                                                                                                        
               bid-price differences                 Detection     Rigging in Public                                                                              identities; category; compare within comparable                                                                                                                                                                                                                                                        
                                                     List          Procurement (2025                                                                              geography; dates      markets                                                                                                                                                                                                                                                                          
                                                                   Update)                                                                                                                                                                                                                                                                                                                                                                                               

  PRICE-003    Winning bid far above    Red Flag     OECD 2025     OECD Guidelines   3.3 Warning signs        Procurements with reliable      Yes                 estimated value;      Estimate quality and      Estimate; award record;     ANOMALY / NO_ANOMALY  Context-dependent   P0               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               estimated value                       Bid-Rigging   for Fighting Bid  related to pricing       estimate and award value                            award value;          market conditions must be price justification         / INSUFFICIENT_DATA                                                                                                                                                                                                        
                                                     Detection     Rigging in Public                                                                              procurement method;   considered; do not equate                                                                                                                                                                                                                                                        
                                                     List          Procurement (2025                                                                              category              overrun with corruption                                                                                                                                                                                                                                                          
                                                                   Update)                                                                                                                                                                                                                                                                                                                                                                                               

  DOC-001      Identical mistakes /     Red Flag     OECD 2025     OECD Guidelines   3.2 Warning signs in     Digital bid documents available Partial             bid documents;        Metadata may be stripped  Original bid files and      ANOMALY / NO_ANOMALY  Context-dependent   P1               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               formatting / metadata                 Bid-Rigging   for Fighting Bid  tender documents                                                             metadata; timestamps; by portals; identical     metadata                    / INSUFFICIENT_DATA                                                                                                                                                                                                        
               across competing bids                 Detection     Rigging in Public                                                                              author fields; text   templates can be                                                                                                                                                                                                                                                                 
                                                     List          Procurement (2025                                                                                                    legitimate                                                                                                                                                                                                                                                                       
                                                                   Update)                                                                                                                                                                                                                                                                                                                                                                                               

  DOC-002      Repeated / suspiciously  Red Flag     DoE           Manual for        Specification            Tender documents with technical Partial             tender text;          Similarity is a lead, not Tender PDF; specification   SIMILARITY_SIGNAL /   Context-dependent   P1               https://doe.gov.in/files/circulars_document/Manual_Goods_2024.pdf                                                                                               2026-08-15
               similar technical                     procurement   Procurement of    principles + fair        specifications                                      specification         proof; account for        section; historical         NO_SIGNAL /                                                                                                                                                                                                                
               specifications                        framework +   Goods, 2nd Ed.,   competition                                                                  clauses; historical   standard                  comparable tenders          INSUFFICIENT_DATA                                                                                                                                                                                                          
                                                     analytical    2024                                                                                           tender corpus;        templates/catalog                                                                                                                                                                                                                                                                
                                                     methodology                                                                                                  category              specifications                                                                                                                                                                                                                                                                   

  ENTITY-001   Shared bidder address /  Red Flag     OECD 2025     OECD Guidelines   3.2 Warning signs in     Where bidder                    Partial             company name;         Entity-resolution         Company                     RELATIONSHIP_SIGNAL / Context-dependent   P1               https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html   2026-08-15
               office / related                      Bid-Rigging   for Fighting Bid  tender documents         identity/registration/address                       registration;         confidence required;      registry/procurement        NO_SIGNAL /                                                                                                                                                                                                                
               identity signal                       Detection     Rigging in Public                          data is available                                   address;              shared address can be     record/source documents     INSUFFICIENT_DATA                                                                                                                                                                                                          
                                                     List          Procurement (2025                                                                              directors/ownership   legitimate                                                                                                                                                                                                                                                                       
                                                                   Update)                                                                                        if lawfully available                                                                                                                                                                                                                                                                                  

  COMP-004     Open participation /     Rule + Red   Department of Manual for        Chapter 3, §3.1 ---      Non-consultancy services; adapt Partial             tender type;          Eligibility should be     Tender document;            FLAG / CLEAR /        Context-dependent   P0               https://doe.gov.in/files/circulars_document/MfPoNCS_2025.pdf                                                                                                    2026-08-15
               restrictive eligibility  Flag         Expenditure   Procurement of    eligibility criteria and equivalent principle to other                       eligibility criteria; based on procurement      eligibility/qualification   INSUFFICIENT_DATA                                                                                                                                                                                                          
               criteria                                            Non-Consultancy   participation            procurement types                                   qualification         requirements/Government   clauses; amendments                                                                                                                                                                                                                                    
                                                                   Services, 2025                                                                                 criteria; category;   policy; distinguish                                                                                                                                                                                                                                                              
                                                                                                                                                                  method                eligibility from                                                                                                                                                                                                                                                                 
                                                                                                                                                                                        qualification; assess                                                                                                                                                                                                                                                            
                                                                                                                                                                                        legitimate specialization                                                                                                                                                                                                                                                        

  COMP-005     Evaluation criteria not  Rule + Red   Department of Manual for        Risk mitigation on       Works procurement; adapt by     Partial             tender document;      Criteria should be        Tender document; evaluation FLAG / CLEAR /        Context-dependent   P0               https://doe.gov.in/files/manuals_documents/Works_Manual_SE_2025.pdf                                                                                             2026-08-15
               objective/proportional   Flag         Expenditure   Procurement of    objective/proportional   procurement method                                  technical criteria;   relevant and              sheets;                     INSUFFICIENT_DATA                                                                                                                                                                                                          
               to requirement                                      Works, Second     technical criteria                                                           scoring scheme;       proportional;             moderation/conciliation                                                                                                                                                                                                                                
                                                                   Edition, 2025                                                                                  qualification         subjectivity should be    records if applicable                                                                                                                                                                                                                                  
                                                                                                                                                                  thresholds            controlled; avoid                                                                                                                                                                                                                                                                
                                                                                                                                                                                        treating strict criteria                                                                                                                                                                                                                                                         
                                                                                                                                                                                        as inherently suspicious                                                                                                                                                                                                                                                         

  PROC-001     Missing / inconsistent   Compliance   Department of GFR 2017, Rule    Rule 159 ---             Central Government procurements Yes if CPPP         tender_id;            Account for GFR           CPPP record; tender notice; FLAG / CLEAR /        Context-dependent   P0               https://doe.gov.in/files/inline-documents/GFR2017.pdf                                                                                                           2026-08-15
               e-publishing of tender,  Rule + Red   Expenditure   159               e-publishing             subject to GFR exceptions       publication data    publication record;   exceptions and            award notice;               INSUFFICIENT_DATA                                                                                                                                                                                                          
               corrigendum or award     Flag                                                                                                  available           corrigenda; award     confidentiality           exception/approval evidence                                                                                                                                                                                                                            
               information                                                                                                                                        publication;          exemptions                                                                                                                                                                                                                                                                       
                                                                                                                                                                  exception flag                                                                                                                                                                                                                                                                                         

  PROC-002     Non-standard procurement Compliance   Department of GFR 2017, Rule    Rule 158 --- methods of  Goods procurement under GFR;    Partial             procurement method;   Single/limited/special    Tender record; procurement  FLAG / CLEAR /        Context-dependent   P1               https://doe.gov.in/files/inline-documents/GFR2017.pdf                                                                                                           2026-08-15
               mode / unexplained       Rule + Red   Expenditure   158               obtaining bids           applicability must be checked                       value; procurement    methods may be legitimate method;                     INSUFFICIENT_DATA                                                                                                                                                                                                          
               deviation from expected  Flag                                                                  against current rules and                           category;             under applicable rules;   approval/justification                                                                                                                                                                                                                                 
               bidding mode                                                                                   exceptions                                          justification;        require justification and                                                                                                                                                                                                                                                        
                                                                                                                                                                  approvals             approvals                                                                                                                                                                                                                                                                        

  COMP-006     Open tender              Rule + Red   Department of Manual for        Chapter 3, §3.1 ---      Non-consultancy services        Partial             eligibility clauses;  Specialized requirements  Tender document; market     FLAG / CLEAR /        Context-dependent   P1               https://doe.gov.in/files/circulars_document/MfPoNCS_2025.pdf                                                                                                    2026-08-15
               participation design     Flag         Expenditure   Procurement of    participation normally                                                       qualification         can legitimately narrow   research; qualification     INSUFFICIENT_DATA                                                                                                                                                                                                          
               appears unnecessarily                               Non-Consultancy   open to all bidders                                                          clauses; bidder       the market; compare with  requirements                                                                                                                                                                                                                                           
               restrictive                                         Services, 2025                                                                                 population; category  market capability and                                                                                                                                                                                                                                                            
                                                                                                                                                                                        procurement need                                                                                                                                                                                                                                                                 
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Methodology

  -----------------------------------------------------------------------
  Concept                             SENTRY treatment
  ----------------------------------- -----------------------------------
  Rules                               Authoritative procurement
                                      requirements/guidance. Do not
                                      convert every guideline into an
                                      automatic fraud rule.

  Red flags                           Established analytical indicators
                                      from authoritative guidance and
                                      established methodologies
                                      (OECD/OCP).

  Benchmarks                          Calculated by SENTRY from
                                      historical comparable procurements;
                                      not copied as arbitrary thresholds
                                      from another system.

  Risk score                          Existing deterministic SENTRY
                                      engine combines validated signals;
                                      score means investigation priority,
                                      not probability of corruption.

  Insufficient data                   First-class outcome. Missing
                                      evidence must not automatically
                                      mean clean or suspicious.

  Context                             Procurement method, category,
                                      geography, value band, time period,
                                      specialized/emergency status and
                                      market conditions should be used
                                      where available.

  Phase 1 scope                       Initial registry is deliberately
                                      small and high-confidence. Expand
                                      after validation on real Indian
                                      procurement data.
  -----------------------------------------------------------------------

## Sheet: Sources

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Source                  Use in SENTRY                 URL
  ----------------------- ----------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------
  Department of           Current official procurement  https://www.doe.gov.in/manuals
  Expenditure --- Manuals manuals index; now includes   
                          Works 2025, Non-Consultancy   
                          Services 2025, Consultancy    
                          Services 2025 and Goods 2024  

  DoE Manual for          Goods procurement             https://doe.gov.in/circulars/manual-procurement-goods-second-edition-2024
  Procurement of Goods    competition, process and      
  --- Second Edition 2024 safeguards                    

  DoE Manual for          Works procurement criteria,   https://doe.gov.in/files/manuals_documents/Works_Manual_SE_2025.pdf
  Procurement of Works    proportionality/objectivity   
  --- Second Edition 2025 and evaluation safeguards     

  DoE Manual for          Participation/eligibility and https://doe.gov.in/files/circulars_document/MfPoNCS_2025.pdf
  Procurement of          procurement competition       
  Non-Consultancy         principles                    
  Services --- 2025                                     

  General Financial Rules Government procurement modes, https://doe.gov.in/files/inline-documents/GFR2017.pdf
  2017                    e-publishing and              
                          e-procurement framework; use  
                          current amendment compilation 
                          when implementing             

  DoE Procurement Policy  Official policy owner for     https://doe.gov.in/procurement-policy-division
  Division                public procurement rules, GFR 
                          procurement administration,   
                          CPPP and e-procurement        

  OECD 2025 Bid-Rigging   Bidding patterns, tender      https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report/component-5.html
  Detection List          documents, pricing and        
                          suspicious behaviour;         
                          includes caution that         
                          indicators are not proof      

  OECD 2025 Executive     Competition, clear            https://www.oecd.org/en/publications/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_cbe05a56-en/full-report/component-2.html
  Summary                 requirements, evaluation      
                          criteria, bid-rigging risk    
                          controls                      

  Open Contracting        73 data-driven red flags with https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/
  Partnership --- 2024    definitions/formulas/data     
  Red Flags               requirements                  

  Competition Commission  Indian legal context for bid  https://www.cci.gov.in/antitrust
  of India --- Antitrust  rigging/collusive bidding     
                          under Section 3(3)            

  CCI Public Procurement  Diagnostics Tool and          https://www.cci.gov.in/public/advocacy/vidoes
  Advocacy                bid-rigging advocacy          
                          materials                     
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Red-Flag Registry

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Red-Flag ID      Indicator Definition      Formula / Detection Logic      Required Fields           False-Positive Considerations                     Confidence Basis      Related    Related        Evidence Required        Output Type           Implementation   Source /
                                                                                                                                                                              Rule ID    Benchmark ID                                                  Priority         Methodology
  ---------------- ------------------------- ------------------------------ ------------------------- ------------------------------------------------- --------------------- ---------- -------------- ------------------------ --------------------- ---------------- --------------
  RF-COMP-001      Single responsive bidder  responsive_bid_count == 1;     tender_id;                PAC/nomination/restricted/specialized/emergency   High when source data COMP-001   BM-COMP-001    tender notice;           SIGNAL                P0               DoE 2024 +
                   / unusually low           contextualize using            responsive_bid_count;     procurement; weak or missing bidder data          is complete and                                 bidder/evaluation                                               SENTRY
                   competition               comparable-tender bidder       bid_count;                                                                  comparable benchmark                            records; award record;                                          contextual
                                             distribution                   procurement_method;                                                         is adequate;                                    benchmark population                                            benchmark
                                                                            category; value;                                                            otherwise                                                                                                       
                                                                            geography; buyer; dates                                                     Medium/Insufficient                                                                                             

  RF-COMP-002      Submission window         submission_days = deadline -   publication_date;         Emergency procurement; justified                  High with complete    COMP-002   BM-COMP-002    notice; timestamps;      SIGNAL                P0               DoE 2024 +
                   unusually short versus    publication; compare with peer deadline; extensions;     extensions/corrigenda; invalid timestamps         dates and adequate                              corrigenda/extensions;                                          SENTRY
                   applicable peers          distribution and documented    procurement_method;                                                         peer sample                                     approval/justification                                          benchmark
                                             extensions                     category                                                                                                                    if available                                                    

  RF-CONC-001      Supplier award            supplier_share =               supplier_id; award_value; Small markets; framework/exclusive arrangements;  Medium/High only with            BM-CONC-001    award records; supplier  SIGNAL                P0               OECD 2025 +
                   concentration materially  supplier_award_value /         category; geography;      specialized suppliers                             adequate population                             identity evidence;                                              SENTRY
                   above peer-market         peer_population_award_value;   buyer; method; dates                                                        and stable entity                               peer-population                                                 benchmark
                   concentration             supplement with HHI/top-k                                                                                  resolution                                      definition                                                      
                                             shares                                                                                                                                                                                                                     

  RF-WIN-001       Repeated winner /         win_rate = supplier_wins /     supplier_id; tender_id;   Dominant qualified supplier; low supplier pool;   Medium/High when                 BM-WIN-001     bid participation and    SIGNAL                P0               OECD 2025 +
                   unusually high supplier   supplier_participations;       participation; winner;    framework contracts                               participation                                   award records                                                   SENTRY
                   win rate                  compare with peer distribution category; geography;                                                        denominator is                                                                                                  benchmark
                                                                            dates                                                                       complete                                                                                                        

  RF-PRICE-001     Identical or              detect exact equality or       tender_id; bidder_id;     Regulated/catalog prices; rounding; standardized  High for exact                   BM-BID-001     bid sheets/BOQ; source   SIGNAL                P0               OECD 2025
                   near-identical bidder     normalized pairwise price      bid_amount; currency;     items; data normalization errors                  matches with reliable                           documents; normalization                                        
                   prices                    distance below validated       quantity; unit; line-item                                                   source data; lower                              metadata                                                        
                                             tolerance                      values                                                                      for approximate                                                                                                 
                                                                                                                                                        matches                                                                                                         

  RF-PRICE-002     Regular/repetitive        measure repeated pairwise      tender_id; bidder_id;     Small bidder populations; formulaic pricing;      Requires sufficient              BM-BID-001     historical bid records;  SIGNAL                P1               OECD 2025
                   bid-price differences     price-gap patterns across      bid_amount; category;     regulated markets                                 repeated                                        peer definition                                                 
                   across tenders            comparable tenders             geography; dates                                                            observations;                                                                                                   
                                                                                                                                                        otherwise                                                                                                       
                                                                                                                                                        Insufficient                                                                                                    

  RF-PRICE-003     Award value unusually     award_to_estimate_ratio =      award_value;              Poor estimate quality; scope change; inflation;   High only with                   BM-PRICE-001 / estimate; award;         SIGNAL                P0               OECD 2025 +
                   high relative to estimate award_value / estimated_value; estimated_value;          specification differences                         reliable                         BM-PRICE-002   BOQ/specification;                                              SENTRY
                   or comparable awards      or normalized unit price       quantity; unit;                                                             estimate/unit                                   comparable awards                                               benchmark
                                             deviation from peers           category/specification;                                                     normalization and                                                                                               
                                                                            dates                                                                       sufficient peers                                                                                                

  RF-PATTERN-001   Bid rotation / geographic detect repeated winner         tender_id; bidder_id;     Legitimate regional specialization; market        Requires longitudinal            BM-WIN-001 /   historical awards;       SIGNAL                P1               OECD 2025
                   allocation pattern        sequences or geographic winner winner; geography;        segmentation; procurement cycles                  evidence; never                  BM-TIME-001    bidder participation;                                           
                                             partitioning beyond expected   category; dates                                                             single-tender                                   geography                                                       
                                             market structure                                                                                           conclusion                                                                                                      

  RF-DOC-001       Identical mistakes /      text/format/metadata           bid_document; text;       Common templates; portal metadata stripping;      High only for                                   original bid files;      SIGNAL                P1               OECD 2025
                   formatting / metadata     similarity above validated     metadata; author;         shared official forms                             multiple independent                            extracted text; metadata                                        
                   across competing bids     threshold, with evidence-level creation_time;                                                              artifacts with                                  snapshot                                                        
                                             match                          submission_time                                                             corroborating                                                                                                   
                                                                                                                                                        evidence                                                                                                        

  RF-ENTITY-001    Shared                    entity-resolution match on     bidder_id; legal_name;    Common registered address can be legitimate;      Confidence must                  BM-REL-001     company/procurement      RELATIONSHIP_SIGNAL   P1               OECD 2025
                   address/office/identity   address, registration or other address; registration_id; entity-resolution false matches                   include match method                            records; source                                                 
                   signal among competing    lawful identifiers             directors/ownership where                                                   and source                                      identifiers                                                     
                   bidders                                                  lawfully available                                                          reliability                                                                                                     

  RF-DOC-002       Repeated/suspiciously     semantic similarity against    tender_text;              Standardized government templates; common catalog Medium until          DOC-002                   tender PDF/page;         SIMILARITY_SIGNAL     P1               DoE 2024 +
                   similar technical         historical comparable tender   specification_text;       specifications                                    validated; similarity                           extracted text; matched                                         SENTRY
                   specifications            specifications; flag only with category; historical                                                        alone is not                                    historical documents                                            document
                                             context                        corpus;                                                                     misconduct                                                                                                      intelligence
                                                                            procurement_method                                                                                                                                                                          
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Detector Output Contract

  -----------------------------------------------------------------------------
  Field               Required          Definition        Example / Allowed
                                                          Values
  ------------------- ----------------- ----------------- ---------------------
  signal              YES               Stable detector   RF-COMP-001 / Single
                                        identifier and    responsive bidder
                                        human-readable    
                                        signal            

  context             YES               Procurement       method=OTE;
                                        context used to   category=road works;
                                        interpret the     value_band=₹1--5Cr
                                        signal            

  benchmark           YES when          Comparable        T1; n=428; median=6;
                      applicable        population, tier, current=1
                                        sample size and   
                                        statistics used   

  evidence            YES               Source records    tender notice +
                                        supporting the    bidder record +
                                        signal; each item source URL
                                        must be traceable 

  confidence          YES               Confidence in the HIGH / MEDIUM / LOW /
                                        signal based on   INSUFFICIENT
                                        data              
                                        completeness,     
                                        source            
                                        reliability and   
                                        benchmark         
                                        adequacy          

  risk_contribution   YES               Contribution to   0--1 normalized
                                        investigation     contribution or
                                        priority, not     configured points
                                        probability of    
                                        corruption        

  explanation         YES               Human-readable    Current bidder count
                                        explanation       is below comparable
                                        generated from    baseline...
                                        structured facts  

  status              YES               Whether detector  SUPPORTED /
                                        can make a valid  NOT_SUPPORTED /
                                        determination     INSUFFICIENT_DATA

  provenance          YES               Rule/benchmark    rule_id;
                                        IDs, source       benchmark_id;
                                        version,          source_snapshot_id;
                                        retrieval         engine_version
                                        timestamp and     
                                        calculation       
                                        version           

  limitations         YES               Known caveats or  No bidder-level price
                                        missing evidence  data available

  review_action       YES               Recommended next  Review tender
                                        human             advertisement and
                                        investigation     qualification
                                        step              criteria
  -----------------------------------------------------------------------------

## Sheet: Phase 1 Checklist

  ---------------------------------------------------------------------------------------------------------------------------
  Component         Status            What is complete                                                Remaining before coding
  ----------------- ----------------- --------------------------------------------------------------- -----------------------
  Rule Registry     COMPLETE          Authority, source, applicability, exceptions, evidence,         Verify exact clause
                                      machine-checkability and priorities documented                  references during
                                                                                                      implementation

  Red-Flag Registry COMPLETE          Definitions, formulas/logic, fields, false-positive notes,      Validate against actual
                                      confidence, rule/benchmark links and evidence documented        SENTRY data
                                                                                                      availability

  Benchmark         COMPLETE          Peer dimensions, statistics, sample policy, tiers, context      Calibrate
  Registry                            adjustments and insufficiency policy documented                 thresholds/statistics
                                                                                                      on real data

  Detector Output   COMPLETE          Standard                                                        Implement shared schema
  Contract                            Signal→Context→Benchmark→Evidence→Confidence→Risk→Explanation   in backend
                                      plus status/provenance/limitations                              

  Phase 1           COMPLETE          Foundation specification is coherent and traceable              Next phase: map current
                                                                                                      code and implement
                                                                                                      registry-backed engine
  ---------------------------------------------------------------------------------------------------------------------------

## Sheet: India Competition Evidence

  ------------------------------------------------------------------------------------------------------------------------
  Source            Finding relevant to     How to use it     URL
                    SENTRY                                    
  ----------------- ----------------------- ----------------- ------------------------------------------------------------
  Competition       CCI identifies bid      Use as Indian     https://www.cci.gov.in/antitrust
  Commission of     rigging/collusive       competition-law   
  India ---         bidding as a horizontal context; do not   
  Antitrust         anti-competitive        turn legal        
  framework         agreement under Section presumption into  
                    3(3), with rebuttable   an automated      
                    presumption.            fraud verdict.    

  CCI --- Eastern   CCI has enforcement     Use enforcement   https://www.cci.gov.in/antitrust/press-release/details/256
  Railway           history involving bid   cases as          
  bid-rigging case  rigging/cartelization   validation        
                    in a tender.            examples/test     
                                            cases, not as     
                                            generic rules.    

  CCI ---           CCI has a published     Use case facts to https://cci.gov.in/antitrust/orders/details/45/0
  Department of     order on alleged        derive            
  Printing case     bid-rigging in          research/test     
                    government tenders.     patterns only     
                                            after legal and   
                                            factual review.   

  CCI --- UP        CCI has a published     Potential Indian  https://cci.gov.in/antitrust/orders/details/623/0
  Agriculture soil  order concerning        case-study        
  testing case      alleged bid-rigging in  benchmark/test    
                    e-tenders.              corpus where      
                                            documents are     
                                            public.           

  CCI Advocacy /    CCI publishes advocacy  Candidate source  https://www.cci.gov.in/public/advocacy/vidoes
  Public            material including a    for future        
  Procurement       Diagnostics Tool for    Red-Flag Registry 
                    Public Procurement      expansion and     
                    Officers and            judge-facing      
                    bid-rigging material.   provenance.       
  ------------------------------------------------------------------------------------------------------------------------

## Sheet: Deep Review Findings

  --------------------------------------------------------------------------
  Finding                 Impact on Phase 1          Action taken
  ----------------------- -------------------------- -----------------------
  DoE's current manual    Phase 1 must cover goods,  Added 2025 Works and
  index is broader than   works and services, not    Non-Consultancy
  the original registry   just goods                 Services sources/rules;
                                                     future registry should
                                                     keep procurement-type
                                                     applicability explicit

  GFR Rule 159 explicitly Data provenance/compliance Added PROC-001
  covers e-publishing     can be a first-class       
                          detector                   

  GFR Rule 158 lists      Method                     Added PROC-002 with
  procurement modes       selection/justification    exception/approval
                          can be audited             requirement

  DoE 2025 Services       Restrictive participation  Added COMP-004 and
  manual says             needs contextual detection COMP-006
  participation should                               
  normally be open and                               
  distinguishes                                      
  eligibility from                                   
  qualification                                      

  DoE 2025 Works manual   Specification/evaluation   Added COMP-005
  emphasizes              checks need                
  relevant/proportional   proportionality rather     
  and objective technical than simple 'strict = bad' 
  criteria                logic                      

  CCI provides Indian     SENTRY can use Indian      Added India Competition
  competition-law context cases for validation/test  Evidence sheet and
  and real enforcement    scenarios, but not as      sources
  cases                   automatic rules            

  OECD explicitly lists   Current red-flag registry  Existing registry
  repeated winners,       should expand beyond the   retained; Phase 2 can
  geographic allocation,  first small set over time  expand systematically
  withdrawals, bid                                   
  rotation, repetitive                               
  price differences,                                 
  winning-bid/estimate                               
  gaps and suspicious                                
  conduct                                            

  OCP provides 73         Useful as a comprehensive  Keep OCP as candidate
  indicators with         candidate library, not a   backlog; validate India
  formulas/data           reason to implement all 73 applicability and data
  requirements            immediately                availability before
                                                     production

  Single bidder is not    Risk engine must use       Retained contextual
  itself proof of         context and benchmark, not COMP-001 + BM-COMP-001
  collusion               a binary fraud rule        
  --------------------------------------------------------------------------

## Sheet: Pre-Coding Master Plan

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Area                Decision / Deliverable         Keep                     Change                  Add                 Remove / Avoid         Definition of Done       Priority
  ------------------- ------------------------------ ------------------------ ----------------------- ------------------- ---------------------- ------------------------ ----------
  Foundation          3 registries + standard        Rule Registry; Benchmark Make Red-Flag Registry  Versioning +        Unversioned ad-hoc     Every production         P0
                      detector contract              Registry                 authoritative           provenance + status thresholds             detector maps to         
                                                                                                                                                 Rule/RedFlag/Benchmark   
                                                                                                                                                 IDs                      

  Detector            Registry-backed risk engine    L1-L6 layered engine     Move                    Registry loader +   Hard-coded universal   Detector output is       P0
  architecture                                                                thresholds/policies to  benchmark service   thresholds             standardized and         
                                                                              config                                                             traceable                

  Benchmarks          Contextual peer baselines      Median/IQR/percentiles   Replace raw global      T0-T3 fallback +    One-size-fits-all      Every benchmark result   P0
                                                                              averages with peer      sample policy +     thresholds             exposes peer definition, 
                                                                              tiers                   time normalization                         n, period, statistic     

  Evidence            Evidence-first investigation   Evidence records +       Make source             Evidence bundle +   AI-generated claims    Every signal has         P0
                                                     provenance               snapshot/version        source reliability  without source         inspectable evidence or  
                                                                              mandatory                                                          INSUFFICIENT_DATA        

  AI                  Explainability/investigation   AI explanations          AI must consume         Evidence-grounded   AI deciding            AI cannot create         P0
                      layer                                                   structured facts        narrative +         guilt/fraud            unsupported facts or     
                                                                                                      question answering                         override deterministic   
                                                                                                                                                 evidence                 

  TenderShield parity 5 feature benchmark            Adopt useful product     Adapt to SENTRY         Feature parity      Copy                   Each feature has         P0
                                                     capabilities             architecture            matrix              branding/claims/code   SENTRY-specific          
                                                                                                                                                 implementation and       
                                                                                                                                                 evidence model           

  Data                Live/public procurement        Current scraped dataset  Formalize source        Scheduler, parser,  Scraping without       Source-specific adapter  P1
                      ingestion                      for demo                 adapters                dedupe, snapshots,  permission in          contract + legal/access  
                                                                                                      retry               production             policy                   

  Validation          Backtesting                    Current demo examples    Create labelled test    Synthetic +         Claiming accuracy      Metrics reported per     P0
                                                                              corpus                  historical +        without labels         detector and dataset     
                                                                                                      case-based                                                          
                                                                                                      validation                                                          

  Deployment          Hackathon demo path            Existing app             Separate demo data from config-driven data  Hard-coded local paths One-command reproducible P1
                                                                              live mode               source; health                             demo                     
                                                                                                      checks                                                              

  Commercialization   Pilot readiness                Investigation dashboard  Add                     RBAC, review queue, Selling 'fraud         Position as risk         P2
                                                                              workflow/audit/export   audit log, API      detection' as          triage/investigation     
                                                                              concepts                                    certainty              intelligence             
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Detector Disposition

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Current / Planned Detector  Decision       Phase    Registry Mapping   Benchmark                What to Change                   Why                        Priority
  --------------------------- -------------- -------- ------------------ ------------------------ -------------------------------- -------------------------- ----------
  Single bidder               KEEP +         2        RF-COMP-001 /      BM-COMP-001              Use responsive bidder count; add Current award-supplier     P0
                              REFACTOR                COMP-001                                    peer context and                 count is not true          
                                                                                                  procurement-method gates         competition measurement    

  Repeat supplier / repeat    KEEP +         2        RF-WIN-001         BM-WIN-001               Use participation denominator    Win rate is more           P0
  winner                      REFACTOR                                                            and peer distribution            meaningful than raw repeat 
                                                                                                                                   count                      

  Buyer concentration         KEEP +         2        RF-CONC-001        BM-CONC-001              Replace fixed 50% threshold with Concentration can be       P0
                              REFACTOR                                                            HHI/top-share + peer baseline    legitimate and             
                                                                                                                                   market-dependent           

  Supplier concentration      KEEP +         2        RF-CONC-001        BM-CONC-001              Same contextual concentration    Avoid universal cutoff     P0
                              REFACTOR                                                            engine                                                      

  Abnormal value              KEEP +         2        RF-PRICE-003       BM-PRICE-001/002         Normalize                        Raw tender-package value   P0
                              REFACTOR                                                            unit/quantity/specification;     is weak evidence           
                                                                                                  compare to peers                                            

  Award clustering            KEEP +         2        RF-PATTERN-001     BM-TIME-001              Use rolling                      Fixed 30-day window is     P1
                              REFACTOR                                                            frequency/inter-arrival          arbitrary                  
                                                                                                  distribution; account for                                   
                                                                                                  procurement cycles                                          

  Suspicious timing           KEEP +         2        COMP-002 / PROC    BM-COMP-002              Compare submission window to     3-day universal threshold  P0
                              REFACTOR                timing                                      applicable rules and peer        is not defensible          
                                                                                                  distribution                                                

  Duplicate description       KEEP +         2        RF-DOC-002         N/A or corpus benchmark  Use normalized/semantic          Exact/near duplicate text  P1
                              REFACTOR                                                            similarity with template         can be legitimate          
                                                                                                  exceptions                                                  

  Missing award data          KEEP           2        Evidence/quality   N/A                      Treat as data-quality/provenance Missing data should not    P0
                                                      signal                                      signal, not fraud signal         create false risk          

  Award \> tender estimate    KEEP +         2        RF-PRICE-003       BM-PRICE-002             Ratio + estimate-quality gate +  Large ratio may be         P0
                              REFACTOR                                                            context                          legitimate                 

  Buyer = supplier            KEEP as        2        RF-ENTITY-001      BM-REL-001               Require verified entity          Possible data/entity       P1
                              RELATIONSHIP                                                        resolution and legal context     issue; not automatic fraud 
                              SIGNAL                                                                                                                          

  Missing documents           KEEP as DATA   2        Evidence contract  N/A                      Separate evidence completeness   Missing evidence should    P0
                              QUALITY                                                             from corruption risk             lower confidence           

  Bid-price similarity        ADD            2        RF-PRICE-001       BM-BID-001               Exact/near-equal normalized      Strongly aligned with OECD P0
                                                                                                  price analysis                   signal family              

  Bid rotation                ADD            2        RF-PATTERN-001     BM-WIN-001/BM-TIME-001   Longitudinal winner-sequence     Needs multiple tenders,    P1
                                                                                                  analysis                         not single-tender          
                                                                                                                                   inference                  

  Geographic allocation       ADD            2        RF-PATTERN-001     BM-WIN-001               Compare winner geography/market  Requires longitudinal      P1
                                                                                                  allocation patterns              market data                

  Bid withdrawal patterns     ADD            2        RF-PATTERN-001     BM-WIN-001               Track withdrawals/participation  OECD-recognized signal     P1
                                                                                                  changes                          family                     

  Restrictive                 ADD            2        COMP-004/005/006   Category/market          NLP + rule checks +              Spec rigging is a core     P0
  eligibility/specification                                              benchmark                proportionality context          entry point                

  E-publishing compliance     ADD            2        PROC-001           N/A                      Check                            GFR Rule 159 gives an      P0
                                                                                                  publication/corrigendum/award    authoritative compliance   
                                                                                                  provenance                       anchor                     

  Procurement mode deviation  ADD            2        PROC-002           N/A                      Detect                           Compliance layer           P1
                                                                                                  method/value/justification       complements anomaly layer  
                                                                                                  inconsistencies                                             

  Vendor risk                 ADD LATER      3        Future vendor      Future                   Build only when reliable lawful  TenderShield feature;      P2
                                                      registry                                    vendor data sources are          data-intensive             
                                                                                                  available                                                   

  Decision audit trail        ADD            2/3      Detector Output    N/A                      Persist reviewer decisions and   Core                       P0
                                                      Contract                                    evidence versions                defensibility/commercial   
                                                                                                                                   feature                    

  Whistleblower triage        ADD LATER      3        Future case-intake N/A                      Separate secure case workflow;   TenderShield feature but   P2
                                                      registry                                    no sensitive-data mixing in      scope-expensive            
                                                                                                  hackathon demo                                              

  Post-award fraud            ADD LATER      3        Future execution   Future                   Invoice/work-completion/entity   Requires post-award        P2
                                                      registry                                    data pipeline                    datasets not guaranteed in 
                                                                                                                                   current scope              
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: TenderShield Parity

  --------------------------------------------------------------------------------------------------------------------------------
  TenderShield    What it claims/does  SENTRY Version          Status     Data Needed              Hackathon   Differentiator for
  Feature                                                                                          Priority    SENTRY
  --------------- -------------------- ----------------------- ---------- ------------------------ ----------- -------------------
  Anomaly         Flags suspicious     Spec/eligibility        PLANNED    Tender text; category;   P0          Evidence-grounded
  Detection       specification        anomaly + benchmark                vendor/market corpus                 and benchmarked
                  language favouring a context                                                                 rather than
                  vendor                                                                                       keyword-only

  Bid Pattern     Identical pricing,   Bid similarity +        PLANNED    Bid-level history;       P0          Longitudinal
  Analysis        rotation, suspicious rotation + withdrawal +            participation; winners               statistical engine
                  withdrawals          geographic allocation                                                   

  Vendor Risk     Aggregates           Supplier profile/risk   LATER      Verified vendor          P2          Only when source
  Scoring         compliance,          layer                              registry,                            quality/legal basis
                  litigation and                                          litigation/performance               is established
                  performance history                                     sources                              

  Decision Audit  Immutable record of  Evidence/provenance +   PLANNED    Signal outputs; reviewer P0          Every risk claim is
  Trail           evaluation decisions reviewer decision log              actions; source                      traceable
                  and reasons                                             snapshots                            

  Whistleblower   Prioritises/routes   Secure case intake +    LATER      Complaint/case data;     P2          Not needed for core
  Triage          complaints with      triage                             access controls                      hackathon demo
                  evidence                                                                                     
  --------------------------------------------------------------------------------------------------------------------------------

## Sheet: Benchmark Design

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Benchmark ID   Peer    Dimensions       Baseline            Statistical Method      Minimum Sample  Refresh          Context Gates                     Output
                 Tier                                                                 Policy                                                             
  -------------- ------- ---------------- ------------------- ----------------------- --------------- ---------------- --------------------------------- -------------------
  BM-COMP-001    T0→T3   method;          Bidder-count        Median; P25/P75; IQR;   Initial \>=30   Daily/weekly     Emergency; specialized;           current; peer_n;
                         category; value  distribution        empirical percentile    comparable      depending data   proprietary; restricted methods   percentile;
                         band; geography;                                             records for     source;                                            baseline; tier;
                         buyer type; time                                             exploratory     recompute on new                                   confidence
                                                                                      percentiles;    data                                               
                                                                                      validate                                                           
                                                                                      empirically                                                        

  BM-COMP-002    T0→T3   method;          Submission-day      Median;                 \>=30 initial   Daily/weekly     Extensions; corrigenda; emergency submission_days;
                         category; value  distribution        P10/P25/P75/P90; IQR    exploratory                                                        percentile;
                         band; geography                                                                                                                 applicable-rule
                                                                                                                                                         status

  BM-CONC-001    T0→T3   category;        Supplier share /    HHI; top-1/top-3 share; Enough awards   Monthly          Framework/exclusive/specialized   share; HHI; peer
                         geography;       HHI                 distribution            to avoid                         markets                           percentile
                         buyer; method;                                               unstable                                                           
                         period                                                       concentration                                                      
                                                                                      estimates                                                          

  BM-WIN-001     T0→T3   category;        Supplier win rate   Win rate;               \>=10           Monthly          Low supplier pool; qualification  win_rate;
                         geography;                           participation-to-win;   comparable                       constraints                       denominator;
                         method; period                       peer distribution       tenders                                                            percentile
                                                                                      initially;                                                         
                                                                                      validate                                                           

  BM-PRICE-001   T0→T3   specification;   Normalized          Median; IQR; P10/P90;   \>=30           Weekly/monthly   Inflation; scope/spec differences normalized_price;
                         unit; quantity;  unit-price          MAD where appropriate   normalized      with time                                          percentile; peer_n
                         category;        distribution                                observations    normalization                                      
                         method;                                                      initially                                                          
                         geography; time                                                                                                                 

  BM-PRICE-002   T0→T3   category;        Award/estimate      Median; IQR; percentile Adequate        Monthly          Estimate quality; scope change;   ratio; percentile;
                         method;          ratio                                       reliable                         negotiation                       estimate_quality
                         geography; time;                                             estimates                                                          
                         value band                                                                                                                      

  BM-BID-001     T0→T3   category;        Bid                 CV; normalized spread;  \>=3 valid bids Monthly          Regulated/catalog prices;         spread; pairwise
                         quantity/unit;   spread/similarity   pairwise distance       per tender;                      standardized items                distance; peer
                         method;          distribution                                enough tenders                                                     percentile
                         geography                                                    for peer                                                           
                                                                                      distribution                                                       

  BM-TIME-001    T0→T3   category;        Inter-award         Median; percentiles;    Adequate        Weekly/monthly   Seasonality; scheduled cycles     interval; rolling
                         geography;       interval / rolling  burst counts            timeline                                                           frequency;
                         buyer; supplier; frequency                                                                                                      percentile
                         period                                                                                                                          

  BM-REL-001     T0→T3   buyer; supplier; Pair award          Share; count; repeat    Repeated        Monthly          Framework/exclusive               pair_share; count;
                         category; period share/frequency     frequency; peer         observations                     supply/specialization             confidence
                                                              comparison              required                                                           
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Data & Evidence Contract

  ----------------------------------------------------------------------------------------------------------------------
  Object          Required Fields      Quality Rules       Evidence Rules        Failure State       Notes
  --------------- -------------------- ------------------- --------------------- ------------------- -------------------
  Tender          tender_id; title;    IDs stable; dates   Store source URL,     INSUFFICIENT_DATA   Core entity
                  buyer; category;     parseable; currency retrieval timestamp,                      
                  method;              normalized          snapshot/hash where                       
                  estimated_value;                         possible                                  
                  publication_date;                                                                  
                  deadline; source_url                                                               

  Bid             tender_id;           Bidder identity     Original bid          INSUFFICIENT_DATA   Competition
                  bidder_id;           resolved;           artifact/reference if                     detectors need
                  bid_amount;          currency/unit       available                                 bidder-level data
                  responsive_status;   normalized                                                    
                  submission_time                                                                    

  Award           tender_id;           Winner linked to    Award notice/source   INSUFFICIENT_DATA   Separate award from
                  winner_id;           bidder/entity;      snapshot                                  participation
                  award_value;         value parseable                                               
                  award_date                                                                         

  Specification   tender_id; text;     OCR/text extraction Page/document         INSUFFICIENT_DATA   NLP only after
                  structured fields if quality tracked     reference + source                        extraction quality
                  available                                snapshot                                  check

  Supplier        supplier_id;         Entity resolution   Source identifier and LOW_CONFIDENCE      Do not merge
                  legal_name; identity confidence stored   match evidence                            entities silently
                  keys                                                                               

  Benchmark       benchmark_id;        Peer population     Store calculation     INSUFFICIENT_DATA   Critical for
  Result          peer_tier; filters;  generated           version + dataset                         reproducibility
                  peer_n; period;      deterministically   snapshot                                  
                  statistic; value                                                                   

  Signal          signal_id; rule_id;  Schema validation   All claims trace to   INSUFFICIENT_DATA   Standard output
                  red_flag_id;         before persistence  evidence/provenance                       contract
                  benchmark_id;                                                                      
                  context; evidence;                                                                 
                  confidence;                                                                        
                  risk_contribution;                                                                 
                  explanation                                                                        

  Review Decision signal_id; reviewer; Decision states     Immutable audit       NOT_REVIEWED        Human-in-the-loop
                  decision; reason;    controlled          record or append-only                     
                  timestamp                                history                                   
  ----------------------------------------------------------------------------------------------------------------------

## Sheet: Validation Plan

  -------------------------------------------------------------------------------------------------------------
  Test Layer     Dataset / Method    What to Measure     Acceptance Target   Why                    Status
                                                         (Initial)                                  Before
                                                                                                    Coding
  -------------- ------------------- ------------------- ------------------- ---------------------- -----------
  Unit tests     Synthetic fixtures  Formula             100% critical-path  Prevents               PLAN
                 for every detector  correctness, edge   tests; explicit     threshold/regression   
                                     cases, missing      insufficient-data   bugs                   
                                     fields              tests                                      

  Backtest       Historical public   Precision/recall    Report metric; do   Measures detector      PLAN
                 tenders with known  where labels exist  not invent target   utility                
                 patterns                                until labelled set                         
                                                         exists                                     

  Case           Public              Whether expected    Qualitative case    Indian-context         PLAN
  validation     CCI/enforcement     signals appear with coverage; no claim  validation             
                 cases + documented  evidence            of causality                               
                 procurement                                                                        
                 examples                                                                           

  Negative       Normal/legitimate   False positive rate Track per detector; Critical for trust     PLAN
  controls       procurement                             set go/no-go                               
                 examples                                thresholds after                           
                                                         baseline                                   

  Ablation       Rules only vs       Ranking stability / Benchmarks should   Proves architecture    PLAN
                 rules+benchmarks vs reviewer usefulness improve contextual  value                  
                 rules+AI                                relevance; AI must                         
                 explanation                             not change                                 
                                                         underlying facts                           

  Benchmark      Rolling historical  Drift / percentile  Monitor sample size Avoid stale baselines  PLAN
  stability      windows             stability           and distribution                           
                                                         drift                                      

  Evidence       Remove source       Confidence/status   Missing evidence    Prevents hallucinated  PLAN
  completeness   fields              behaviour           =\> lower           certainty              
                 intentionally                           confidence or                              
                                                         INSUFFICIENT_DATA                          
  -------------------------------------------------------------------------------------------------------------

## Sheet: AI Boundary

  -------------------------------------------------------------------------------------------------
  Component        AI Allowed?    Role                        Must Not Do        Required Grounding
  ---------------- -------------- --------------------------- ------------------ ------------------
  Risk score       NO             Consume deterministic       Invent risk score  Structured signal
                                  signals and configured      or override rule   objects
                                  contributions               logic              

  Benchmarking     NO for         May explain computed        Make up comparator Benchmark result
                   baseline       statistics                  population         object
                   calculation                                                   

  Specification    YES            Semantic                    Declare            Source tender
  NLP                             similarity/classification   corruption/fraud   text + similarity
                                  as a signal generator                          evidence

  Explanation      YES            Translate structured        Add facts not      Evidence bundle +
                                  evidence into               present in         rule/benchmark
                                  investigator-readable       evidence           metadata
                                  explanation                                    

  Investigation    YES            Answer questions over       Cite unsupported   Retrieval +
  assistant                       stored evidence             external facts as  citations/source
                                                              if observed        IDs

  Case             LIMITED        Rank by configured risk     Profile people     Structured risk +
  prioritization                  contribution and confidence beyond lawful      access controls
                                                              procurement data   

  Final decision   NO             Human reviewer              Declare            Human review +
                                                              guilt/corruption   evidence
  -------------------------------------------------------------------------------------------------

## Sheet: Hackathon Scope

  ---------------------------------------------------------------------------------------------------------
  Scope          Feature                      MVP         Stretch        Out of Scope     Demo Proof
  -------------- ---------------------------- ----------- -------------- ---------------- -----------------
  Core           Contextual competition       YES         Live benchmark Nationwide all   Show 1-bid tender
                 anomaly                                  refresh        categories       vs 428 peers

  Core           Price anomaly                YES         Bid-level pair Full commodity   Show normalized
                                                          analysis       price            price percentile
                                                                         intelligence     

  Core           Supplier                     YES         Network graph  Full vendor due  Show
                 concentration/repeat winner                             diligence        buyer-supplier
                                                                                          history

  Core           Specification                YES         LLM-assisted   Automated legal  Show matched
                 similarity/restrictiveness               evidence       judgement        clauses + source
                                                          summary                         

  Core           Evidence/audit trail         YES         Immutable      Blockchain       Click signal →
                                                          event store                     source →
                                                                                          calculation

  Core           Decision audit trail         YES         Multi-user     Enterprise RBAC  Reviewer
                                                          workflow                        accepts/rejects
                                                                                          signal

  TenderShield   Vendor risk scoring          NO          Prototype      Litigation       Show roadmap, not
  parity                                                  profile card   scraping         fake completeness

  TenderShield   Whistleblower triage         NO          Prototype      Production       Show roadmap, not
  parity                                                  intake         sensitive-data   fake completeness
                                                                         handling         

  TenderShield   Post-award fraud             NO          Prototype      Invoice          Show roadmap, not
  parity                                                  execution gap  integration      fake completeness
  ---------------------------------------------------------------------------------------------------------

## Sheet: Phase 2 Roadmap

  ---------------------------------------------------------------------------------------------------------------
  Step        Workstream      Deliverable Before Code      Implementation    Exit Criteria            Priority
                                                           Later                                      
  ----------- --------------- ---------------------------- ----------------- ------------------------ -----------
  2.1         Current-state   Detector Disposition +       Refactor          Every existing detector  P0
              mapping         file/function map            detectors         has                      
                                                                             KEEP/CHANGE/REMOVE/ADD   
                                                                             decision                 

  2.2         Registry schema JSON/YAML/DB schema derived  Registry loader + Registry can be          P0
                              from Excel                   validation        loaded/versioned without 
                                                                             code edits               

  2.3         Benchmark       Peer tiers + statistics +    Benchmark service Deterministic benchmark  P0
              engine design   sample policies                                result object            

  2.4         Evidence layer  Source/snapshot/provenance   Evidence store +  Every signal has         P0
                              contract                     validators        evidence or explicit     
                                                                             insufficiency            

  2.5         Risk model      Risk contribution policy     Risk aggregator   No hard-coded            P0
                                                                             unexplained weights      

  2.6         Detectors       Detector-by-detector specs   Implement P0      Unit + fixture tests     P0
                                                           detectors first   pass                     

  2.7         NLP             Specification                Embedding/model   Similarity output is     P1
                              similarity/restrictiveness   service           explainable and          
                              design                                         source-grounded          

  2.8         Audit workflow  Reviewer state machine       Review UI/API     Decision history is      P1
                                                                             traceable                

  2.9         Validation      Test corpus + metrics plan   Backtest harness  Metrics published        P0
                                                                             internally               

  2.10        Demo            Demo scenario + seeded       Frontend polish   3-minute deterministic   P0
                              data + evidence                                demo works offline       
  ---------------------------------------------------------------------------------------------------------------

## Sheet: Open Decisions

  --------------------------------------------------------------------------------------
  Decision          Current Recommendation      Reason                 Needs Human
                                                                       Confirmation?
  ----------------- --------------------------- ---------------------- -----------------
  Single bidder     No universal threshold;     Avoid false positives  NO
  threshold         benchmark + context         and arbitrary rules    

  Minimum benchmark 30 initial exploratory      Engineering starting   YES before
  sample            observations; validate      point, not government  production
                    empirically                 rule                   

  Risk score        Investigation priority, not Legally/analytically   NO
  semantics         probability of corruption   safer and more         
                                                defensible             

  AI authority      Explanation/investigation   Prevents hallucinated  NO
                    only                        or opaque verdicts     

  TenderShield      Phase 3                     Requires reliable      NO
  vendor risk                                   lawful external data   

  Whistleblower     Phase 3                     Security/privacy scope NO
  module                                        too large for core     
                                                hackathon              

  Post-award fraud  Phase 3                     Needs                  NO
                                                invoice/execution      
                                                datasets               

  Five-feature      Implement anomaly, bid      Best effort/value      YES for exact
  parity            patterns, audit trail now;  balance                hackathon scope
                    vendor risk + whistleblower                        
                    later                                              

  Live scraping     Demo can use prepared       Avoid making           YES
                    snapshots; production       unsupported claims     
                    requires                    about live access      
                    permission/terms/source                            
                    policy                                             

  Rule provenance   Every rule has              Core defensibility     NO
                    authority/source/section                           
                    and verification date                              
  --------------------------------------------------------------------------------------

## Sheet: Pattern Intelligence

  ----------------------------------------------------------------------------------------------------------------------------------------------------------
  Layer           Question a human          Machine representation                            Example         Why it matters           SENTRY action
                  investigator asks                                                                                                    
  --------------- ------------------------- ------------------------------------------------- --------------- ------------------------ ---------------------
  1\. Baseline    Is this actually unusual  Peer population + percentile + distribution       1 bidder, but   Avoid false positives    Never score a red
                  for this market/context?                                                    category                                 flag before
                                                                                              normally has                             contextual baseline
                                                                                              1--2 bidders                             

  2\. Sequence    What happened before and  Time-series events + state transitions            Supplier A wins Collusion is often       Build tender-event
                  after this tender?                                                          → B withdraws → longitudinal             timeline
                                                                                              A wins again                             

  3\.             Who repeatedly interacts  Buyer-supplier-bidder graph                       Same 4          Single events can look   Add graph/network
  Relationship    with whom?                                                                  suppliers       normal; network reveals  features
                                                                                              repeatedly      structure                
                                                                                              appear in same                           
                                                                                              tenders                                  

  4\.             Do multiple bidders       Pairwise/cross-tender similarity features         Same price gap, Coordination can         Add pairwise +
  Coordination    behave too similarly?                                                       same submission manifest across          longitudinal features
                                                                                              timing, same    independent tenders      
                                                                                              document                                 
                                                                                              fingerprint                              

  5\.             Do losing bidders still   Winner→subcontractor/partner transition           B loses         Potential                Track post-award
  Substitution    benefit after losing?                                                       repeatedly but  cover-bid/suppression    relationships when
                                                                                              gets            pattern                  data exists
                                                                                              subcontracted                            
                                                                                              by A                                     

  6\. Market      Does                      Conditional win shares by region/category/buyer   A wins north, B Possible market          Add
  allocation      geography/product/buyer                                                     south with      allocation               geographic/category
                  appear partitioned?                                                         unusually                                allocation features
                                                                                              stable                                   
                                                                                              boundaries                               

  7\.             Who should have bid but   Expected-participation model                      Regular         Suppression/withdrawal   Model participation
  Participation   did not?                                                                    supplier stops  signal                   history, not just
                                                                                              bidding only                             bidder count
                                                                                              when A                                   
                                                                                              participates                             

  8\. Price       Are prices merely high,   Rank, spread, pairwise gaps, repeated deltas      A always        Structure is stronger    Use cross-tender
  structure       or structurally                                                             lowest; B/C     than one abnormal price  price-pattern
                  coordinated?                                                                remain fixed                             features
                                                                                              +3%/+5%                                  

  9\. Document    Do bids look              Text/format/metadata fingerprints                 Same typo +     Independent submissions  Evidence signal;
  provenance      independently prepared?                                                     same metadata   may share artifacts      never sole proof
                                                                                              author/time                              

  10\.            Could tender design       Eligibility/qualification/specification/context   Specialized     Alternative explanation  Add rule-based
  Procurement     itself explain the        flags                                             requirement     is essential             design-context layer
  design          pattern?                                                                    explains low                             
                                                                                              participation                            

  11\. Data       Could the pattern be      Completeness + source confidence                  Only award      Prevents false certainty Confidence downgrade
  quality         caused by                                                                   winner is                                / INSUFFICIENT_DATA
                  missing/incorrect data?                                                     available, no                            
                                                                                              losing bids                              

  12\.            What legitimate           Exception/context features + counterfactual       Emergency       Human-like reasoning     Store alternative
  Alternative     explanation could produce checks                                            procurement     requires competing       explanations
  explanation     the same signal?                                                            explains short  hypotheses               
                                                                                              window                                   

  13\. Evidence   Do independent signals    Signal co-occurrence + evidence diversity         Rotation +      Multiple independent     Build pattern bundle,
  convergence     point in the same                                                           price           signals are stronger     not simple sum
                  direction?                                                                  similarity +                             
                                                                                              shared docs                              

  14\.            Can we explain the        Structured event graph → grounded narrative       5 tenders, 3    Human review is          Generate
  Investigator    pattern as a coherent                                                       suppliers, 2    narrative, not isolated  evidence-grounded
  narrative       timeline?                                                                   regions, 14     alerts                   investigation brief
                                                                                              months                                   
  ----------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Human Investigation Model

  ---------------------------------------------------------------------------
  Investigation     Human Reasoning   SENTRY Implementation Output
  Stage                                                     
  ----------------- ----------------- --------------------- -----------------
  Detect            Something looks   Detector generates    Signal
                    unusual           candidate signal      

  Contextualize     Is unusual        Peer benchmark +      Context +
                    actually unusual  procurement context   benchmark
                    here?                                   

  Connect           What other        Entity resolution +   Related
                    events/entities   graph + time window   events/entities
                    are related?                            

  Compare           What happened in  Comparable tender     Peer comparison
                    similar tenders?  retrieval             

  Challenge         What legitimate   Exception rules +     Alternative
                    explanation       alternative           explanations
                    exists?           hypotheses            

  Corroborate       Do independent    Cross-signal evidence Pattern bundle
                    signals agree?    convergence           

  Verify            Can I inspect the Evidence              Evidence bundle
                    source?           snapshot/page/URL +   
                                      calculation           
                                      provenance            

  Prioritize        Which case        Risk contribution +   Investigation
                    deserves human    confidence + evidence priority
                    attention first?  quality               

  Decide            Is there enough   Human reviewer only   Review decision
                    to act?                                 
  ---------------------------------------------------------------------------

## Sheet: Pattern Feature Library

  ------------------------------------------------------------------------------------------------------------------------------
  Pattern ID       Pattern Family  Features            Minimum Data     Method                    Confidence Rule     Phase
  ---------------- --------------- ------------------- ---------------- ------------------------- ------------------- ----------
  PAT-TIME-001     Temporal        inter-award         Multiple tenders Rolling windows;          Require             2
                                   intervals; rolling  over time        percentiles;              longitudinal sample 
                                   wins; bursts;                        change-point/sequence                         
                                   sequence entropy                     features                                      

  PAT-WIN-001      Winner Rotation A→B→C→A sequences;  Winner history + Markov/sequence           Never infer from    2
                                   alternating         tender ordering  statistics + permutation  \<3 comparable      
                                   winners; winner                      baseline                  events              
                                   entropy                                                                            

  PAT-GEO-001      Geographic      winner share by     Winner +         Conditional shares +      Need sufficient     2
                   Allocation      geography;          geography +      deviation from expected   regional            
                                   supplier-region     category         allocation                observations        
                                   exclusivity                                                                        

  PAT-PART-001     Participation   expected bidder     Bidder           Historical participation  Need stable         2
                   Suppression     probability;        participation    model                     participation       
                                   non-participation   history                                    history             
                                   after prior bids                                                                   

  PAT-BID-001      Bid Similarity  pairwise normalized Bid-level prices Pairwise distance +       Need comparable     2
                                   price gap; rank     across tenders   cross-tender repetition   bids and            
                                   correlation;                                                   normalization       
                                   repeated deltas                                                                    

  PAT-DOC-001      Document        text similarity;    Digital bid      TF-IDF/embedding +        Template-aware;     2
                   Similarity      formatting          documents        metadata fingerprint      corroboration       
                                   fingerprint;                                                   required            
                                   metadata similarity                                                                

  PAT-REL-001      Relationship    buyer-supplier      Resolved         Graph degree, edge        Entity-resolution   2
                   Graph           frequency; bidder   entities +       weight,                   confidence required 
                                   co-occurrence;      tender history   community/co-occurrence                       
                                   supplier pairs                                                                     

  PAT-SUB-001      Post-Loss       loser→winner        Award +          Transition/edge analysis  Only when reliable  3
                   Relationship    subcontracting; JV  subcontract/JV                             post-award data     
                                   transitions         data                                       exists              

  PAT-PRICE-001    Price Structure winning spread;     Bid prices +     Robust statistics;        Need normalized     2
                                   second-best         estimates +      distribution comparison   comparable prices   
                                   closeness; repeated comparable specs                                               
                                   ratios; unexplained                                                                
                                   changes                                                                            

  PAT-DESIGN-001   Tender Design   eligibility         Tender text +    Rule/NLP classification + Human review for    2
                                   strictness;         structured       market comparison         legal               
                                   qualification       criteria                                   interpretation      
                                   concentration;                                                                     
                                   specification                                                                      
                                   similarity                                                                         

  PAT-CONV-001     Evidence        co-occurrence of    Multiple         Weighted evidence         Cannot substitute   2
                   Convergence     independent signal  detector outputs diversity / calibrated    for source evidence 
                                   families                             model later                                   

  PAT-ALT-001      Alternative     emergency;          Method +         Exception rules +         Required before     2
                   Explanation     specialization;     category +       counterfactual benchmark  high-priority       
                                   market monopoly;    context                                    conclusion          
                                   seasonality;                                                                       
                                   framework                                                                          
  ------------------------------------------------------------------------------------------------------------------------------

## Sheet: Pattern Validation

  ---------------------------------------------------------------------------------
  Test                      What it proves    Example           Pass Condition
  ------------------------- ----------------- ----------------- -------------------
  Synthetic rotation test   Engine detects    12 tenders with   Pattern signal
                            controlled        intentional       appears; legitimate
                            A→B→C→A pattern   rotation          random sequence
                                                                stays low

  Geographic partition test Engine            A wins North, B   Stable allocation
                            distinguishes     South repeatedly  scores higher after
                            random geography                    sample threshold
                            from stable                         
                            allocation                          

  Participation suppression Engine detects    B bids normally   Conditional
  test                      supplier          except when A     participation
                            disappearance     appears           anomaly appears
                            conditioned on                      
                            competitor entry                    

  Price-gap repetition test Engine detects    B = A + 3% across Repeated gap signal
                            repeated pairwise many comparable   appears; one-off
                            deltas            tenders           gap does not

  Document fingerprint test Engine finds      Same typo + same  Signal requires
                            corroborating     metadata          multiple artifacts
                            artifacts                           

  Alternative-explanation   Engine does not   Emergency         Risk contribution
  test                      overflag          procurement /     is reduced or
                            legitimate        specialized       status becomes
                            contexts          market            contextual

  Missing-data test         Engine avoids     No bidder-level   Status =
                            false certainty   data              INSUFFICIENT_DATA
                                                                or confidence
                                                                reduced

  Convergence test          Multiple weak     rotation +        Bundle ranking
                            signals form      price +           rises only with
                            stronger case     participation +   independent
                                              document evidence evidence
  ---------------------------------------------------------------------------------

## Sheet: Candidate Pattern Library

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ID       Pattern                     Family            Current State      Core Features                     False Positive / Caveat             Priority   Source Families    Minimum Data                      Detection Approach
  -------- --------------------------- ----------------- ------------------ --------------------------------- ----------------------------------- ---------- ------------------ --------------------------------- ---------------------
  PAT-01   Single / low bidder         Competition       Current            Bidder count; responsive bidder   Do not equate low count with        P0         OCP; OECD; Indian  Bid-level data +                  Benchmark + context +
                                                                            count; bid participation          wrongdoing; compare peers                      procurement        method/category/value/geography   evidence
                                                                                                                                                             context                                              

  PAT-02   High concentration /        Concentration     Current            HHI; top-1/top-3 share; win rate  Legitimate                          P0         OCP; OECD          Award + participation history     Peer distribution +
           repeated winner                                                                                    monopoly/specialization/framework                                                                   market context
                                                                                                              can explain                                                                                         

  PAT-03   Winner rotation             Collusion /       New                A→B→C sequences; alternation;     Short series can produce            P0         OECD; OCP          Ordered tender history            Longitudinal
                                       sequence                             transition matrix                 random-looking rotation                                                                             benchmark + sequence
                                                                                                                                                                                                                  test

  PAT-04   Geographic allocation       Collusion /       New                Supplier win share by geography;  Regional specialization can be      P1         OECD; OCP          Winner + geography + category     Conditional
                                       market allocation                    stable partitions                 legitimate                                                                                          allocation benchmark

  PAT-05   Repeated bid-price gap      Pricing /         New                Pairwise normalized price delta   Catalog/regulated pricing can cause P0         OECD; OCP          Bid-level prices + comparable     Robust pairwise
                                       coordination                         repeated across tenders           repetition                                                        specs                             distribution

  PAT-06   Suspiciously similar bid    Pricing /         New                CV; normalized spread; rank       Identical standard prices can be    P0         OECD; OCP          Bid-level prices                  Peer distribution +
           prices                      coordination                         similarity                        legitimate                                                                                          item normalization

  PAT-07   Bid withdrawal /            Participation     New                Withdrawal rate; conditional      Operational capacity/qualification  P1         OECD; OCP          Bid events over time              Conditional
           non-participation pattern                                        participation                     can explain                                                                                         participation
                                                                                                                                                                                                                  benchmark

  PAT-08   Competitor-conditioned      Participation     New                P(bid \| competitor present) vs   Small sample and supplier           P1         OECD/OCP-derived   Participation history             Conditional
           participation suppression                                        baseline                          specialization                                                                                      probability + minimum
                                                                                                                                                                                                                  sample

  PAT-09   Repeated supplier pair /    Network           New                Co-occurrence frequency; pair     Market structure can naturally      P1         OCP; OECD          Bidder history                    Network baseline
           co-bidding                                                       edge weight                       create clusters                                                                                     

  PAT-10   Buyer-supplier relationship Network           Current/refactor   Pair share; repeat frequency      Framework/exclusive contracts       P0         OCP; procurement   Award history + procurement type  Peer baseline +
           concentration                                                                                                                                     context                                              exception rules

  PAT-11   Bidder document similarity  Document /        New                Text similarity;                  Common templates can create         P1         OECD; OCP          Digital bid docs                  Multi-artifact
                                       coordination                         formatting/metadata fingerprints  similarity                                                                                          corroboration

  PAT-12   Same typo / metadata        Document /        New                Rare phrase/typo/metadata overlap Shared consultants/templates        P1         OECD-derived; case Bid documents + metadata          Rarity +
           artifact                    coordination                                                                                                          validation                                           corroboration

  PAT-13   Specification similarity /  Procurement       New                Similarity to prior               Specialized procurement can require P0         DoE; OCP; OECD     Tender text + qualification data  Rule + market
           restrictive criteria        design                               vendor-favouring specs;           narrow criteria                                                                                     comparison
                                                                            qualification concentration                                                                                                           

  PAT-14   Eligibility/qualification   Procurement       New                Threshold percentile vs           High thresholds can be objectively  P1         DoE; OCP           Tender criteria + peer corpus     Peer percentile +
           outlier                     design                               comparable tenders                necessary                                                                                           proportionality
                                                                                                                                                                                                                  review

  PAT-15   Short submission window     Process / timing  Current/refactor   Submission days vs applicable     Emergency/extension/corrigendum     P0         DoE/GFR; OCP; OECD Publication/deadline events       Applicable-rule
                                                                            rule + peer distribution                                                                                                              check + benchmark

  PAT-16   Corrigendum / deadline      Process / timing  New                Number/timing/content of          Normal clarification can cause      P1         DoE/GFR; OCP       Tender versions + timestamps      Version timeline
           manipulation pattern                                             amendments; deadline shifts       amendments                                                                                          

  PAT-17   Award-to-estimate anomaly   Pricing           Current/refactor   Award/estimate ratio percentile   Poor estimate quality; scope change P0         OCP; procurement   Estimate + award + scope          Estimate-quality
                                                                                                                                                             guidance                                             gate + benchmark

  PAT-18   Bid spread anomaly          Pricing           New                Winner-second spread; dispersion  Few bidders naturally produce large P0         OECD; OCP          Bid-level prices                  Peer distribution
                                                                            vs peers                          spread                                                                                              

  PAT-19   Repeated near-identical     Pricing /         New                Repeated losing price             Standardized pricing                P1         OECD; OCP          Bid-level longitudinal data       Pairwise +
           losing bids                 coordination                         ratios/ordering                                                                                                                       longitudinal test

  PAT-20   Bidder entry/exit anomaly   Participation     New                New entrant rate; sudden exits by Business cycles/capacity changes    P1         OCP-derived        Bidder history                    Change-point + market
                                                                            buyer/category                                                                                                                        context

  PAT-21   Unusual tender clustering   Temporal          Current/refactor   Rolling tender/award frequency    Seasonality and budget cycles       P1         OCP-derived        Tender timestamps                 Seasonal baseline

  PAT-22   Repeated award timing to    Temporal /        New                Inter-award intervals; burstiness Scheduled/framework procurement     P1         OCP-derived        Award history                     Seasonality + peer
           same supplier               relationship                                                                                                                                                               comparison

  PAT-23   Buyer-supplier-bidder       Network           New                Community structure; edge         Small markets naturally form dense  P1         OCP; OECD-derived  Resolved entities + history       Graph baseline
           network anomaly                                                  concentration; repeated subgraphs graphs                                                                                              

  PAT-24   Winner-loser transition /   Post-award        New                Loser→winner subcontract/JV       Legitimate subcontracting/JV        P2         OECD/OCP-derived   Post-award relationships          Verified relationship
           post-loss relationship                                           transition                                                                                                                            evidence

  PAT-25   Bid submission timestamp    Coordination      New                Time delta clustering;            Portal batching / timezone /        P1         OECD-derived       Bid submission timestamps         Portal-aware
           similarity                                                       same-minute/hour patterns         automation                                                                                          normalization

  PAT-26   Identical bid arithmetic /  Document /        New                Repeated rounding, arithmetic,    Templates/software can explain      P2         OECD-derived       Bid documents                     Multi-artifact
           formatting                  coordination                         formatting fingerprints                                                                                                               corroboration

  PAT-27   Non-standard procurement    Compliance        New                Method vs                         Exceptions may be legitimate        P1         GFR Rule 158       Method + approvals +              Rule applicability +
           method / unexplained                                             value/category/justification                                                                        justification                     evidence
           deviation                                                                                                                                                                                              

  PAT-28   E-publishing / award        Compliance / data New                Missing/inconsistent publication  GFR exceptions/confidentiality      P0         GFR Rule 159       Publication records               Compliance status +
           publication anomaly         quality                              events                                                                                                                                exception evidence

  PAT-29   Buyer=supplier/entity       Entity            Current/refactor   Resolved entity relationship      Data/entity resolution errors       P1         Procurement        Entity registry + IDs             High-confidence
           relationship anomaly                                                                                                                              controls; data                                       entity resolution
                                                                                                                                                             quality                                              

  PAT-30   Missing evidence / data     Evidence quality  Current            Required-field completeness;      Source outage/incomplete            P0         SENTRY evidence    Source records                    Confidence downgrade;
           completeness anomaly                                             source freshness                  publication                                    model                                                never fraud score
                                                                                                                                                                                                                  alone

  PAT-31   Multiple independent signal Meta-pattern      New                Signal family diversity; temporal Correlated signals can double-count P0         OCP/OECD           Multiple detector outputs         Calibrated evidence
           convergence                                                      overlap; evidence diversity                                                      methodology                                          convergence
                                                                                                                                                             principle                                            

  PAT-32   Alternative explanation /   Meta-pattern      New                Emergency/specialization/market   Requires contextual data            P0         DoE/OECD/OCP       Context + peer data               Reduce risk or mark
           counterfactual check                                             monopoly/seasonality controls                                                    principles                                           contextual

  PAT-33   Change-point in             Temporal          New                Pre/post behavior distribution    Contract changes/market shocks      P1         OCP-derived        Longitudinal history              Change-point + event
           supplier/buyer behavior                                          shift                                                                                                                                 context

  PAT-34   Market-share shock around   Market            New                Supplier share before/after       Legitimate contract cycle           P2         OCP/OECD-derived   Market history                    Before/after
           procurement event                                                buyer/category change                                                                                                                 benchmark

  PAT-35   Repeated tender template    Design/document   New                Template similarity + targeted    Legitimate template updates         P2         OCP/DoE-derived    Tender versions + corpus          Semantic diff +
           reuse with vendor-specific                                       clause changes                                                                                                                        contextual review
           changes                                                                                                                                                                                                

  PAT-36   Specification-to-winner     Design /          New                Winning supplier capability terms Winner may simply be best fit       P1         OCP/DoE-derived    Tender spec + supplier capability Counterfactual/peer
           similarity                  relationship                         vs restrictive specs                                                                                data                              comparison
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: Pattern Source Crosswalk

  -------------------------------------------------------------------------------------------------------------
  Pattern ID     Primary Reference Family     Risk Domain           India Applicability Note     Priority
  -------------- ---------------------------- --------------------- ---------------------------- --------------
  PAT-01         OCP red flags; OECD          Competition /         India-specific rule context  P0
                 bid-rigging indicators       participation         required                     

  PAT-02         OCP; OECD repeated           Concentration         Need                         P0
                 winners/concentration                              market-definition/context    

  PAT-03         OECD bid rotation; OCP red   Collusion sequence    Needs longitudinal tender    P0
                 flags                                              history                      

  PAT-04         OECD geographic allocation;  Market allocation     Need geography and enough    P1
                 OCP                                                observations                 

  PAT-05         OECD repetitive price        Bid price patterns    Need comparable bid          P0
                 differences; OCP                                   normalization                

  PAT-06         OECD bid price similarity;   Pricing               Need item/spec normalization P0
                 OCP                                                                             

  PAT-07         OECD withdrawals; OCP        Participation         Need bid-event data          P1

  PAT-08         Derived from OCP/OECD        Participation         Requires conditional history P1
                 participation concepts                                                          

  PAT-09         OCP/OECD co-bidding patterns Network               Entity resolution required   P1

  PAT-10         OCP                          Network               Framework/exclusive          P0
                 concentration/relationship                         exceptions                   
                 concepts                                                                        

  PAT-11         OECD suspicious              Document              Templates create false       P1
                 conduct/document indicators                        positives                    

  PAT-12         OECD suspicious bid          Document              Rare artifact evidence only  P1
                 artifacts (methodological)                                                      

  PAT-13         DoE manuals + OCP/OECD       Procurement design    Legal interpretation remains P0
                 tender-design indicators                           human                        

  PAT-14         DoE                          Procurement design    Proportionality/context      P1
                 eligibility/qualification                          required                     
                 principles + OCP                                                                

  PAT-15         GFR/DoE + OCP/OECD timing    Process               Must check applicable        P0
                                                                    procurement                  
                                                                    method/exceptions            

  PAT-16         DoE/GFR + OCP                Process               Need versioned tender        P1
                                                                    documents                    

  PAT-17         OCP + procurement guidance   Pricing               Estimate quality is critical P0

  PAT-18         OECD bid spread + OCP        Pricing               Need bid-level prices        P0

  PAT-19         OECD repetitive pricing      Pricing               Need repeated comparable     P1
                 patterns                                           tenders                      

  PAT-20         OCP-derived participation    Participation         Market shocks possible       P1
                 anomaly                                                                         

  PAT-21         OCP-derived timing           Temporal              Seasonality required         P1

  PAT-22         OCP-derived                  Temporal              Frameworks can explain       P1
                 timing/relationship                                bursts                       

  PAT-23         OCP/OECD-derived network     Network               Need entity resolution       P1

  PAT-24         OCP/OECD-derived post-award  Post-award            Needs subcontract/JV data    P2
                 relationships                                                                   

  PAT-25         OECD-derived suspicious      Coordination          Portal batching caveat       P1
                 submission behavior                                                             

  PAT-26         OECD-derived bid artifact    Document              Need digital docs            P2
                 concepts                                                                        

  PAT-27         GFR Rule 158                 Compliance            Applicability + approval     P1
                                                                    evidence                     

  PAT-28         GFR Rule 159                 Compliance            Exceptions/confidentiality   P0
                                                                    handling                     

  PAT-29         Data quality + procurement   Entity                Not a fraud signal alone     P1
                 controls                                                                        

  PAT-30         OCP data-quality             Evidence              Should affect confidence,    P0
                 principles + SENTRY evidence                       not fraud score              
                 model                                                                           

  PAT-31         OCP/OECD multi-indicator     Meta-pattern          Avoid double counting        P0
                 approach                                           correlated signals           

  PAT-32         DoE/OECD/OCP contextual      Meta-pattern          Required before strong       P0
                 safeguards                                         prioritization               

  PAT-33         Derived longitudinal anomaly Temporal              Need enough history          P1

  PAT-34         Derived market-share pattern Market                Needs reliable market        P2
                                                                    universe                     

  PAT-35         Derived tender-document      Design/document       Need corpus and version      P2
                 comparison                                         history                      

  PAT-36         Derived design-to-winner     Design/relationship   Need capability/market data  P1
                 relationship                                                                    
  -------------------------------------------------------------------------------------------------------------

## Sheet: Pattern Priority Matrix

  -------------------------------------------------------------------------------------------------
  Priority       Meaning          Pattern Families      Data Dependency              Target
  -------------- ---------------- --------------------- ---------------------------- --------------
  P0             Core defensible  Single/low bidder;    Bid-level + tender-level +   Hackathon +
                 detectors        concentration; winner source evidence              first
                                  rotation; repeated                                 production
                                  price gap; bid                                     pilot
                                  similarity;                                        
                                  restrictive criteria;                              
                                  short window;                                      
                                  award/estimate; bid                                
                                  spread; e-publishing;                              
                                  evidence                                           
                                  completeness;                                      
                                  convergence;                                       
                                  alternative                                        
                                  explanation                                        

  P1             Longitudinal /   Geographic            Longitudinal history +       Post-MVP
                 network          allocation;           entity resolution + richer   
                 expansion        withdrawal;           documents                    
                                  participation                                      
                                  suppression;                                       
                                  co-bidding;                                        
                                  documents;                                         
                                  corrigenda; bidder                                 
                                  entry/exit; timing;                                
                                  networks; timestamps;                              
                                  method deviation;                                  
                                  entity anomalies;                                  
                                  change points;                                     
                                  spec-to-winner                                     

  P2             Advanced /       Post-loss             Post-award/vendor/document   Later product
                 data-intensive   relationships;        metadata datasets            
                                  market-share shock;                                
                                  metadata/arithmetic                                
                                  fingerprints;                                      
                                  template evolution                                 
  -------------------------------------------------------------------------------------------------

## Sheet: Ecosystem Intelligence

  -----------------------------------------------------------------------------------------------------------------------------
  Layer             What SENTRY should know Signals / Features           Evidence              Priority    Important limitation
  ----------------- ----------------------- ---------------------------- --------------------- ----------- --------------------
  Tender            Complete procurement    notice, corrigenda,          Original              P0          Missing lifecycle
                    lifecycle               deadline, bids, evaluation,  tender/versioned                  events must lower
                                            award, cancellation,         snapshots                         confidence
                                            amendments                                                     

  Buyer / Procuring Institution-level       tender volume, categories,   Official tender/award P0          Do not infer
  Entity            procurement history     average competition, repeat  history                           misconduct from
                                            suppliers, concentration,                                      concentration alone
                                            procurement methods                                            

  Supplier          Procurement history and wins, participation, win     Tender/bid/award      P0          Separate observed
                    capability context      rate, categories, geography, records; official                 facts from inferred
                                            buyer mix, value             registries where                  capability
                                            distribution, bid patterns   lawful                            

  Supplier          Could supplier          category history, contract   Tender                P1          Capability inference
  capability        plausibly execute this  scale, technical             qualifications +                  must be
                    procurement?            qualifications, geography,   public                            evidence-backed; no
                                            stated capabilities          business/registry                 unsupported 'front
                                                                         evidence                          company' claims

  Supplier          Resolve organizations   legal name, registration     Official              P1          Use
  ownership /       and relationships       identifiers, aliases,        corporate/registry                organization-level
  entity identity                           directors/beneficial         sources                           public data; avoid
                                            ownership where                                                exposing unnecessary
                                            lawfully/publicly available                                    personal data

  Past tenders      Longitudinal history    same buyer, same supplier,   Historical tender     P0          Need comparable
                                            same category, previous      corpus                            population and
                                            winner/loser/participation                                     stable IDs
                                            patterns                                                       

  Prior cases /     Known official          CCI orders, court/public     Primary official      P1          A case/allegation is
  enforcement       enforcement history     enforcement records,         orders/records                    not proof of current
                                            debarment/blacklisting where                                   wrongdoing; status
                                            officially published                                           must be explicit

  News / articles   External context around credible reporting,          Publisher + article   P1          News is contextual
                    tender/entities         investigation articles,      date + URL +                      evidence, not
                                            adverse-event timeline       retrieval timestamp               authoritative proof;
                                                                                                           corroborate

  Legal /           Publicly documented     case type, court/forum,      Official court/public P1          Do not imply guilt
  litigation        proceedings relevant to status, date, relation to    records where                     from pending/closed
  context           entity/procurement      entity/tender                available                         cases

  Debarment /       Eligibility/status      debarment status, issuing    Official              P0          Must check date and
  suspension        context                 authority, start/end dates,  blacklist/debarment               scope; stale status
                                            scope                        notice                            must not be treated
                                                                                                           as current

  Relationships     Buyer-supplier-bidder   co-bidding, repeat awards,   Entity-resolution     P1          Relationship ≠
                    ecosystem graph         shared                       evidence + source                 wrongdoing;
                                            addresses/registrations when provenance                        confidence and
                                            public, common directors                                       source quality
                                            where lawfully available,                                      required
                                            JV/subcontract links                                           

  Tender↔supplier   Historical fit for      same category, similar       Comparable tender     P0          Benchmark against
  fit               exact procurement       scale, geography, method,    history + tender                  peers; don't create
                                            qualification match          criteria                          deterministic
                                                                                                           capability verdict

  Tender↔news       Event timeline around   news before/after tender,    Timestamped           P2          Search/retrieval
  context           procurement             entity mentions,             articles + source                 layer should be
                                            project/sector events        metadata                          separated from risk
                                                                                                           engine

  Post-award        What happened after     subcontract/JV, amendments,  Post-award records    P2          Needs reliable
  ecosystem         award                   cancellation,                                                  execution data
                                            delivery/performance signals                                   
                                            when public                                                    

  Market ecosystem  Who else could          peer supplier universe,      Historical            P1          Market universe must
                    reasonably compete?     entry/exit, concentration,   procurement +                     be defined
                                            geographic coverage          category data                     transparently

  Human             One coherent 'kundali'  timeline, entities,          All cited evidence    P0          AI summarizes;
  investigation     without unsupported     patterns, benchmarks, cases, bundles                           deterministic engine
  brief             claims                  news, evidence gaps,                                           remains source of
                                            alternative explanations                                       risk signals
  -----------------------------------------------------------------------------------------------------------------------------

## Sheet: Entity Profile Schema

  -------------------------------------------------------------------------------------------------
  Profile        Core fields            Historical       External context           Risk treatment
                                        features                                    
  -------------- ---------------------- ---------------- -------------------------- ---------------
  Tender Profile ID; buyer; category;   prior tenders;   project/sector news;       Tender risk =
                 value; method; dates;  amendments;      official notices           signals +
                 source                 bidder counts;                              context
                                        awards                                      

  Buyer Profile  legal/institution      tender volume;   official                   Context, not
                 name; identifiers;     supplier         procurement/oversight      guilt
                 department             concentration;   notices                    
                                        method                                      
                                        distribution;                               
                                        repeat awards                               

  Supplier       legal name; public     wins; losses;    official registries;       Observed
  Profile        registration IDs;      participation;   debarment; CCI/court       facts +
                 aliases                win rate; buyer  records; credible news     confidence
                                        mix; category                               
                                        mix; geography;                             
                                        value                                       
                                        distribution                                

  Relationship   entity A/B;            frequency;       official                   Relationship
  Profile        relationship type;     first/last seen; corporate/JV/subcontract   signal, never
                 source                 co-occurrence;   evidence                   automatic
                                        transitions                                 misconduct

  Case Profile   entity/tender;         date; status;    official order/judgment    Status-aware;
                 authority/court; case  outcome; scope                              allegation ≠
                 ID if public                                                       finding

  News Profile   entity/tender/topic;   recurring        article text/metadata      Contextual
                 publisher; URL; date   themes; event                               evidence with
                                        timeline                                    source quality
  -------------------------------------------------------------------------------------------------

## Sheet: Ecosystem Source Registry

  ----------------------------------------------------------------------------------------------------------------
  Source Family          Use                    Preferred      Data Extracted        Reliability   Rule
                                                Source                               Tier          
  ---------------------- ---------------------- -------------- --------------------- ------------- ---------------
  Official procurement   Tender lifecycle +     CPPP /         tender, corrigendum,  A             Primary source
                         award                  procuring      bids/award where                    
                                                authority      public                              
                                                portals                                            

  DoE / GFR              Procurement rules and  Department of  rule/section/manual   A             Authoritative
                         applicability          Expenditure                                        rule source

  CCI                    Competition            Competition    orders, cases,        A             Status-aware;
                         enforcement/context    Commission of  advocacy guidance                   not a generic
                                                India                                              risk score

  Courts / official case Legal proceedings      Official       case/status/order     A/B           Use status and
  records                                       court/public   metadata                            relevance
                                                records where                                      filters
                                                accessible                                         

  Corporate registry     Entity                 Official       organization          A             Minimize
                         resolution/corporate   MCA/registry   identifiers,                        personal data
                         context                data where     filings/public fields               
                                                lawfully                                           
                                                accessible                                         

  Debarment/blacklists   Eligibility/status     Official       entity, scope, dates  A             Date/scope
                                                authority                                          mandatory
                                                notices                                            

  Credible news          External context       Established    article, date, entity B             Never sole
                                                publishers /   mentions                            basis for
                                                publisher                                          misconduct
                                                archives                                           claim

  Research / OECD / OCP  Pattern methodologies  OECD/OCP       red flags, formulas,  B             Methodology,
                                                               methodological                      not Indian
                                                               guidance                            legal rule
  ----------------------------------------------------------------------------------------------------------------

## Sheet: Ecosystem Safety Rules

  ----------------------------------------------------------------------------------
  Rule                    Requirement                        Why
  ----------------------- ---------------------------------- -----------------------
  FACT/INFERENCE          Store observed fact separately     Prevents AI turning a
  SEPARATION              from model inference               pattern into an
                                                             allegation

  STATUS AWARENESS        Cases/news/debarment must carry    Old or dismissed
                          current status and date            matters can otherwise
                                                             mislead

  SOURCE PROVENANCE       Every external claim stores        Makes investigation
                          source, URL, publication/retrieval auditable
                          time                               

  CORROBORATION           News must not independently        Media can be incomplete
                          generate a high-risk verdict       or wrong

  RELATIONSHIP ≠          Shared                             Avoids false
  MISCONDUCT              director/address/co-bidding/etc.   accusations
                          are relationship signals only      

  NO PRIVATE DATA HUNTING Use only necessary lawful/public   Keeps system defensible
                          organization-level information     and privacy-conscious

  ALTERNATIVE EXPLANATION Every high-priority pattern checks Human-style
                          legitimate explanations            investigation requires
                                                             competing hypotheses

  TEMPORAL VALIDITY       Every status has                   A past debarment or
                          effective/observed date            case cannot be treated
                                                             as current

  ENTITY RESOLUTION       Never merge similarly named        Critical source of
  CONFIDENCE              entities without evidence          false positives

  HUMAN REVIEW            High-impact findings require       SENTRY is investigation
                          reviewer confirmation              intelligence, not a
                                                             guilt adjudicator
  ----------------------------------------------------------------------------------

## Sheet: P0 P1 P2 Data Model

  -----------------------------------------------------------------------------------------------------------------------------
  Domain          P0 Fields                   P1 Fields               P2 Fields               Primary Source    Used For
  --------------- --------------------------- ----------------------- ----------------------- ----------------- ---------------
  Tender          tender_id, buyer_id, title, corrigendum_count,      full document           Official          Risk +
                  category, estimated_value,  version_history,        embeddings, amendment   procurement       context +
                  procurement_method,         qualification_text,     semantic diffs,         portal            evidence
                  publish_date, deadline,     specification_text,     post-award delivery                       
                  award_date, status,         bid_events                                                        
                  source_url, snapshot_id                                                                       

  Bid             bid_id, tender_id,          withdrawal_reason,      metadata fingerprint,   Tender/bid        P0 risk + P1
                  supplier_id, submitted_at,  document_fingerprint,   arithmetic fingerprint, records           pattern
                  bid_value, responsive_flag  bid_document_id,        text embeddings                           
                                              qualification_result                                              

  Award           award_id, tender_id,        amendments,             execution/performance   Official          Risk + context
                  supplier_id, award_value,   final_contract_value    events                  award/contract    
                  award_date, status                                                          records           

  Buyer           buyer_id, legal_name,       historical tender       organizational          Official records  Benchmark +
                  department, identifiers     stats, supplier         network/context                           context
                                              concentration, method                                             
                                              distribution                                                      

  Supplier        supplier_id, legal_name,    wins, losses,           ownership/beneficial    Official          Benchmark +
                  public identifiers, aliases participation,          ownership where         registries +      context
                                              win_rate,               lawfully public,        procurement       
                                              category/geography mix, capability embeddings                     
                                              value distribution                                                

  Relationship    relationship_id, entity_a,  edge_weight,            subcontract/JV          Official/public   Context;
                  entity_b,                   co-bidding_count,       transitions, richer     sources           selected graph
                  relationship_type,          repeat_award_count      network features                          signals
                  source_id, observed_from,                                                                     
                  observed_to                                                                                   

  Case            case_id, entity_id,         relevance_to_tender,    case-document           Official          Context only
                  authority, case_type,       scope                   embeddings              authority/court   unless
                  filed_date, status,                                                         records           independently
                  outcome, source_url                                                                           validated

  News            article_id,                 event_type,             semantic                Credible public   Investigator
                  entity/tender/topic,        relevance_score,        clustering/event graph  publishers        context only
                  publisher,                  corroboration_count                                               
                  publication_date, url,                                                                        
                  retrieval_time                                                                                

  Benchmark       benchmark_id,               seasonality,            adaptive/calibrated     SENTRY derived    Risk
                  population_definition,      buyer/supplier baseline models                  from historical   normalization
                  dimension_set, sample_size,                                                 data              
                  baseline,                                                                                     
                  percentile_method,                                                                            
                  refresh_date                                                                                  

  Evidence        evidence_id, source_type,   page/section/quote      cross-source            All sources       Auditability
                  source_url, snapshot_id,    locator, hash           corroboration graph                       
                  retrieved_at, claim,                                                                          
                  source_quality                                                                                

  Investigation   investigation_id,           timeline,               AI narrative + reviewer SENTRY derived    Human review
                  tender_id, signals,         related_entities,       annotations                               
                  benchmark_refs,             pattern_bundle                                                    
                  evidence_refs,                                                                                
                  alternative_explanations,                                                                     
                  confidence                                                                                    
  -----------------------------------------------------------------------------------------------------------------------------

## Sheet: Entity Resolution Model

  -----------------------------------------------------------------------------------------------
  Stage             Method                     Input          Output              Confidence /
                                                                                  Gate
  ----------------- -------------------------- -------------- ------------------- ---------------
  1\. Exact         Registration/tender IDs    Official IDs   Canonical entity ID High if
  identifier        where available                                               authoritative

  2\. Exact         Case-folding, punctuation, Legal names    Candidate matches   Never
  normalized name   legal suffix normalization                                    auto-merge on
                                                                                  name alone

  3\. Alias mapping Known aliases/trading      Historical     Alias→canonical     Source-backed
                    names                      records        mapping             

  4\.               Public organization        Organization   Supporting match    Supporting only
  Address/contact   address/contact where      records        features            
  signal            relevant                                                      

  5\. Corporate     Official public filings /  Entity records Relationship edge   Source + date
  relation          registrations where lawful                                    required

  6\. Historical    Same                       Tender history Probabilistic match Never sole
  behavior          buyer/category/geography                  support             identifier
                    patterns                                                      

  7\. Human review  Ambiguous/high-impact      Candidate      Approved/rejected   Required for
                    merges                     match bundle   link                high-impact
                                                                                  ambiguity

  8\. Provenance    Store why entities were    All match      Resolution record   Auditable
                    linked                     evidence                           
  -----------------------------------------------------------------------------------------------

## Sheet: Ecosystem Graph Model

  ----------------------------------------------------------------------------
  Node Type           Key Attributes    Important Edges   Pattern Uses
  ------------------- ----------------- ----------------- --------------------
  Tender              ID, buyer,        PUBLISHED_BY,     Tender lifecycle,
                      category, value,  RECEIVED_BID,     design, timing
                      dates, method     AWARDED_TO,       
                                        AMENDED_BY        

  Buyer               ID, department,   ISSUED,           Concentration,
                      geography         AWARDED_TO        repeat awards

  Supplier            ID, category,     BID_ON, WON, LOST Win patterns,
                      geography                           participation

  Bid                 ID, value, time,  SUBMITTED_BY,     Price/timestamp
                      response status   FOR_TENDER        patterns

  Person/Officer (if  Only necessary    DIRECTOR_OF,      Relationship
  lawfully/publicly   public role       OFFICER_OF        context; not
  available)          identifiers                         automatic risk

  Organization        Legal/public      OWNS/RELATED_TO   Entity
                      identifiers       where lawfully    resolution/network
                                        public            

  Case                Authority,        INVOLVES,         Context only
                      status, date      RELATES_TO        

  News Event          Publisher, date,  MENTIONS,         Timeline/context
                      topic             RELATES_TO        only

  Document            Source,           SUPPORTS,         Evidence provenance
                      hash/snapshot     ATTACHED_TO       

  Market/Category     Category,         HAS_SUPPLIER,     Comparable benchmark
                      geography, time   CONTAINS_TENDER   universe
                      window                              
  ----------------------------------------------------------------------------

## Sheet: Risk vs Context Matrix

  -----------------------------------------------------------------------------------------
  Information        Risk Score?       Context?       Evidence       Reason
                                                      Required?      
  ------------------ ----------------- -------------- -------------- ----------------------
  Single/low bidder  YES,              YES            YES            Core procurement
                     contextualized                                  signal

  Winner rotation    YES               YES            YES            Longitudinal pattern

  Repeated price gap YES               YES            YES            Quantitative pattern

  Supplier win       YES               YES            YES            Needs market/peer
  concentration                                                      context

  Restrictive        YES, cautiously   YES            YES            Requires rule
  qualification                                                      applicability +
  signal                                                             context

  Short tender       YES, only against YES            YES            Emergency/exceptions
  window             applicable rule                                 matter

  Official debarment YES,              YES            YES            Date/scope must match
  active at tender   high-confidence                                 
  date               compliance signal                               

  Past CCI/court     NO direct fraud   YES            YES            Past case ≠ current
  case               score                                           wrongdoing

  News article       NO direct fraud   YES            YES            Contextual, not
                     score                                           authoritative proof

  Shared             NO alone          YES            YES            Relationship ≠
  director/address                                                   misconduct

  Co-bidding         POSSIBLY          YES            YES            Needs baseline and
  relationship                                                       corroboration

  Missing data       NO positive risk  YES            YES            Reduce confidence
                     by itself                                       instead

  Alternative        NO                YES            YES            Can reduce
  explanation                                                        prioritization

  Evidence           YES as meta-layer YES            YES            Must avoid
  convergence                                                        double-counting
                                                                     correlated signals

  AI narrative       NO                YES            YES            AI explains evidence;
                                                                     does not create risk

  Human reviewer     NO automated      YES            YES            Final decision remains
  decision           score                                           human
  -----------------------------------------------------------------------------------------

## Sheet: P0 Data Contracts

  -----------------------------------------------------------------------------------------------
  Object         Required Fields          Validation        Derived Features      Downstream
  -------------- ------------------------ ----------------- --------------------- ---------------
  Tender         tender_id; buyer_id;     IDs unique; dates duration_days;        Rules,
                 title; category; value;  ordered; value    award_ratio;          benchmarks,
                 method;                  nonnegative;      bidder_count;         patterns
                 publish/deadline/award   source present    lifecycle             
                 dates; status; source;                     completeness          
                 snapshot                                                         

  Bid            bid_id; tender_id;       Foreign keys      rank;                 Price +
                 supplier_id;             valid; timestamp  normalized_price;     competition
                 submitted_at; bid_value; valid; value      spread; participation patterns
                 response                 nonnegative                             

  Supplier       supplier_id; legal_name; Canonical ID +    win_rate;             Benchmarks +
                 identifiers; aliases     resolution status participation_rate;   graph
                                                            buyer/category        
                                                            concentration         

  Award          award_id; tender_id;     Supplier/tender   award/estimate ratio; Risk + context
                 supplier_id;             exist; date valid repeat winner         
                 award_value; date                                                

  Evidence       evidence_id; source;     Every claim       source_quality;       Audit trail
                 URL; retrieved_at;       traceable         freshness             
                 snapshot; claim                                                  

  Benchmark      population_definition;   Minimum sample    percentile/z/robust   Risk
                 dimensions; sample_size; threshold;        deviation             normalization
                 baseline; method;        reproducible                            
                 refresh                  query                                   
  -----------------------------------------------------------------------------------------------

## Sheet: P0 Detector Specifications

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Detector ID   Detector        Inputs                  Core Calculation      Benchmark / Population        Exceptions / Controls   Evidence         Confidence       Risk Contribution           Output
  ------------- --------------- ----------------------- --------------------- ----------------------------- ----------------------- ---------------- ---------------- --------------------------- ----------------------
  P0-COMP-01    Single / Low    responsive_bid_count,   Signal when bidder    Comparable tenders by         specialized             tender notice,   data             bounded competition         signal, benchmark,
                Bidder          category, buyer,        count is materially   category+buyer/method+value   procurement,            bid/award        completeness ×   contribution; no direct     explanation,
                                geography, method,      below comparable      band+geography; require       emergency/exception,    records,         source quality × guilt inference             confidence,
                                value, date             distribution; 1       minimum sample                low supplier universe;  benchmark query  benchmark                                    evidence_refs
                                                        bidder alone is not                                 missing bid data lowers                  strength ×                                   
                                                        sufficient                                          confidence                               context                                      

  P0-COMP-02    Repeat Winner / supplier wins,          win concentration and Buyer/category/time           framework contracts,    historical award history depth +  bounded concentration       supplier history +
                Concentration   participation,          repeat-winner streak  population; use share,        specialized supplier    records          entity           contribution                benchmark +
                                buyer/category history  vs comparable market  percentile, streak statistics market, legitimate                       resolution                                   alternatives
                                                                                                            incumbency                               confidence +                                 
                                                                                                                                                     benchmark sample                             

  P0-COMP-03    Winner Rotation winner sequence,        detect recurring      Comparable sequential tenders small sample, changing  award history +  sequence         bounded network/sequence    pattern instances +
                                supplier IDs, tender    rotation/sequence     by buyer/category/time        supplier universe,      sequence         length +         contribution                significance/context
                                sequence                structures above                                    framework arrangements  evidence         completeness +                               
                                                        baseline                                                                                     resolution                                   

  P0-PRICE-01   Repeated Price  bid values, ranks,      pairwise normalized   Comparable tenders with ≥2    regulated/catalog       bid records +    bid              bounded pricing             gap statistics +
                Gap             supplier IDs, tender    gaps across           valid bids; robust gap        prices, rounding,       calculation      completeness +   contribution                affected pairs +
                                IDs                     comparable tenders;   distribution                  missing bid values      trace            sample size +                                evidence
                                                        detect unusually                                                                             source quality                               
                                                        repeated gaps                                                                                                                             

  P0-PRICE-02   Bid Similarity  bid values; optional    price                 Comparable bid population;    standardized official   bid records;     data             bounded pricing             similarity metric +
                                document features       similarity/repeated   use distribution/percentile   rates, small markets,   document         completeness +   contribution                benchmark +
                                                        identical or          rather than arbitrary         rounding                evidence only if method validity                              explanation
                                                        near-identical bids   universal threshold                                   available                                                     
                                                        after normalization                                                                                                                       

  P0-PRICE-03   Award /         estimated_value,        normalized            Same                          negotiation rules,      tender + award + field            bounded value anomaly       ratio + percentile +
                Estimate        award_value, comparable award/estimate ratio  buyer/category/method/value   framework pricing,      amendments       completeness +                               amendments
                Anomaly         awards                  compared with         band/time where possible      scope changes, missing                   benchmark                                    
                                                        comparable                                          estimate revisions                       strength                                     
                                                        distribution                                                                                                                              

  P0-PRICE-04   Bid Spread      bid values, responsive  dispersion/spread of  Same                          few bidders,            bid records +    bid count +      bounded pricing/competition spread metrics +
                Anomaly         status                  valid bids vs         category/buyer/method/value   heterogeneous scope,    benchmark        comparability    contribution                benchmark
                                                        comparable tenders    band                          regulated prices        population                                                    

  P0-TIME-01    Applicable      publish_date, deadline, submission duration   Applicable procurement rule + emergency procurement,  original         rule             bounded process-design      duration + applicable
                Timing Anomaly  method, exceptions,     compared with         buyer/category historical     method-specific         notice + rule    applicability    contribution                rule + exception
                                amendments              applicable            baseline                      exception,              source +         confidence +                                 analysis
                                                        rule/benchmark; flag                                extension/corrigendum   timeline         timeline                                     
                                                        only when                                                                   snapshots        completeness                                 
                                                        rule/benchmark                                                                                                                            
                                                        context supports it                                                                                                                       

  P0-DATA-01    Evidence / Data required fields, source calculate             Expected field set for        portal gaps,            source           completeness     normally no risk; reduce    data gaps + affected
                Completeness    snapshots, lifecycle    completeness by       tender/method                 unpublished bid data,   inventory +      score            confidence                  detectors
                                events                  detector and tender;                                inaccessible docs       retrieval logs                                                
                                                        never turn                                                                                                                                
                                                        missingness into                                                                                                                          
                                                        positive risk                                                                                                                             

  P0-RULE-01    Active          supplier identity,      match active official Official authority record     expired/out-of-scope    official         authoritative    high-confidence compliance  status + scope +
                Eligibility /   official status,        restriction to                                      status, ambiguous       order/notice +   source + exact   signal when exact match     evidence
                Debarment Match effective dates, scope, supplier and tender                                 entity identity         dates            identity +                                   
                                tender date             date/scope                                                                                   date/scope match                             

  P0-META-01    Evidence        outputs from            combine corroborating Signal-family diversity and   correlated signals,     all linked       source quality + meta-level prioritization   convergence summary +
                Convergence     independent detector    signal families with  evidence quality              duplicate sources,      evidence         independence +   adjustment, not arbitrary   correlated-signal
                                families                correlation                                         common underlying                        completeness     additive score              handling
                                                        guardrails; avoid                                   variable                                                                              
                                                        double counting                                                                                                                           

  P0-META-02    Alternative     pattern, tender         generate/check        Rule/market/tender context    absence of evidence is  supporting       explanation      can reduce                  pattern → explanation
                Explanation     context, rules,         legitimate                                          not proof explanation   records +        evidence quality confidence/prioritization   → evidence → residual
                                category, geography,    explanations and                                    is false                rule/context                                                  anomaly
                                market                  evidence; reduce                                                            evidence                                                      
                                                        priority when                                                                                                                             
                                                        strongly supported                                                                                                                        
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Sheet: P0 Implementation Task Map

  ------------------------------------------------------------------------------------------------------------------------------------
  Order       Workstream      Implementation Task                                  Depends On      Deliverable      Acceptance Gate
  ----------- --------------- ---------------------------------------------------- --------------- ---------------- ------------------
  1           Repository      Map current SENTRY modules, data flow, APIs,         Existing repo   Architecture     No coding until
              audit           frontend, existing detectors; identify duplicates                    delta document   current system is
                                                                                                                    understood

  2           Canonical       Implement                                            Excel data      Validated        Fixtures can load
              schema          Tender/Bid/Award/Buyer/Supplier/Evidence/Benchmark   model           models +         and validate
                              schemas with stable IDs                                              migrations       

  3           Entity          Implement identifier-first matching + provenance +   Canonical       Resolution       Known
              resolution      ambiguity queue                                      schema          service + audit  same/different
                                                                                                   records          entity fixtures
                                                                                                                    pass

  4           Evidence store  Store URL, snapshot/reference, retrieved_at, claim,  Schema          Evidence         Every detector
                              source quality, provenance                                           API/storage      result links to
                                                                                                                    evidence

  5           Benchmark       Comparable population builder + minimum sample +     Schema +        Benchmark        Same input/query
              engine          reproducible statistics                              history         service          produces same
                                                                                                                    benchmark

  6           P0 competition  Implement single/low bidder, concentration, rotation Benchmark       Detectors +      Synthetic and
                                                                                   engine          tests            historical
                                                                                                                    fixtures pass

  7           P0 pricing      Implement repeated gap, similarity, award/estimate,  Benchmark       Detectors +      False-positive
                              spread                                               engine          tests            controls pass

  8           P0 timing/rules Implement timing anomaly + active                    Rule registry + Rule-aware       Exceptions and
                              eligibility/debarment matching                       evidence        detectors        date/scope tests
                                                                                                                    pass

  9           Meta reasoning  Implement evidence convergence + alternative         All P0          Prioritization   Correlated signals
                              explanation framework                                detectors       layer            are not
                                                                                                                    double-counted

  10          Ecosystem graph Create nodes/edges for                               Entity          Graph/query      Historical
                              tender/buyer/supplier/bid/relationship/evidence      resolution      layer            relationship
                                                                                                                    queries work

  11          Investigation   Return signals, benchmarks, evidence, confidence,    All prior       Investigation    One tender can
              API             alternatives, data gaps                              layers          JSON contract    produce an
                                                                                                                    auditable case

  12          Frontend        Investigation view: timeline, network, benchmarks,   Investigation   UI panels        Every displayed
                              evidence, explanations                               API                              claim traceable

  13          Backtesting     Run P0 on historical/synthetic datasets; measure     All P0          Evaluation       Thresholds/logic
                              stability/false positives                                            report           adjusted from
                                                                                                                    evidence, not
                                                                                                                    intuition

  14          AI layer        Grounded summarization over structured evidence only Investigation   Cited            AI cannot invent
                                                                                   API             investigation    sources/facts
                                                                                                   brief            

  15          Security/ops    Logging, rate limits, retries, source access         All external    Operational      No bypass of
                              compliance, secrets                                  integrations    controls         access controls
  ------------------------------------------------------------------------------------------------------------------------------------

## Sheet: P0 Test Matrix

  ----------------------------------------------------------------------------------------
  Test ID        Area            Scenario            Expected Result        Severity
  -------------- --------------- ------------------- ---------------------- --------------
  T01            Competition     1 bidder in         Low/neutral signal;    Critical
                                 specialized market  specialization context 
                                 with historically   surfaced               
                                 1-2 bidders                                

  T02            Competition     1 bidder where      Competition signal     Critical
                                 comparable median   with benchmark         
                                 is 7 and sample is  evidence               
                                 adequate                                   

  T03            Concentration   Supplier wins most  Context explains       Critical
                                 tenders in          concentration; no      
                                 legitimate          automatic high risk    
                                 framework                                  

  T04            Rotation        Artificial repeated Rotation pattern       High
                                 winner sequence     detected               

  T05            Pricing         Repeated identical  Pricing signal         High
                                 gap across          detected with          
                                 unrelated           traceable calculation  
                                 comparable tenders                         

  T06            Pricing         Standard            Alternative            Critical
                                 regulated/catalog   explanation            
                                 pricing creates     suppresses/qualifies   
                                 similar bids        signal                 

  T07            Award           Award/estimate      Amendment context      High
                                 ratio unusual but   qualifies anomaly      
                                 amended estimate                           
                                 explains it                                

  T08            Timing          Short deadline      No timing risk;        Critical
                                 under valid         exception evidence     
                                 emergency exception shown                  

  T09            Timing          Short deadline      Timing signal with     High
                                 without applicable  rule/benchmark         
                                 exception           evidence               

  T10            Identity        Two suppliers have  Remain separate        Critical
                                 similar names but   entities               
                                 different IDs                              

  T11            Identity        Same official       Merge confidently with Critical
                                 registration ID     provenance             
                                 across records                             

  T12            Debarment       Restriction expired No active eligibility  Critical
                                 before tender       signal                 

  T13            Debarment       Restriction active  High-confidence        Critical
                                 and scope matches   compliance signal      
                                 tender                                     

  T14            Evidence        Source unavailable  Claim marked           Critical
                                 for a claim         unsupported/data gap;  
                                                     no fabricated evidence 

  T15            Meta            Four correlated     Do not count as four   Critical
                                 price metrics from  independent signals    
                                 same bid values                            

  T16            News            Credible article    Context shown with     Critical
                                 reports an          allegation status; no  
                                 allegation          direct guilt score     

  T17            News            Official order      Context/evidence       High
                                 corroborates        strengthened with      
                                 relevant event      primary source         

  T18            Missing data    Bid documents       Confidence decreases;  Critical
                                 unavailable         risk does not increase 
                                                     solely from            
                                                     missingness            

  T19            Alternative     Legitimate          Priority reduced and   Critical
                                 explanation         explanation displayed  
                                 strongly supported                         

  T20            Audit           Investigator clicks Original               Critical
                                 a signal            source/evidence and    
                                                     calculation trace are  
                                                     available              
  ----------------------------------------------------------------------------------------

## Sheet: P0 Output Contract

  ------------------------------------------------------------------------------------------------
  Field                      Type              Meaning                           Required
  -------------------------- ----------------- --------------------------------- -----------------
  case_id                    string            Investigation/case identifier     YES

  tender_id                  string            Canonical tender identifier       YES

  priority                   enum              LOW / MEDIUM / HIGH / REVIEW      YES

  signals                    array             Individual detector outputs       YES

  signal_id                  string            Detector identifier               YES

  signal_value               number/object     Raw calculated result             YES

  benchmark                  object            Population, sample, baseline and  YES when
                                               method                            applicable

  context                    array             Relevant                          YES
                                               tender/buyer/supplier/ecosystem   
                                               context                           

  evidence_refs              array             Traceable evidence IDs            YES

  confidence                 number            Confidence in the signal/evidence YES
                                               chain                             

  alternative_explanations   array             Legitimate explanations and       YES
                                               supporting evidence               

  data_gaps                  array             Missing/uncertain inputs          YES
                                               affecting interpretation          

  risk_contribution          number/object     Bounded contribution to           YES for scored
                                               prioritization                    signals

  explanation                string            Grounded human-readable           YES
                                               explanation                       

  source_provenance          object            Source/query/version/retrieval    YES
                                               metadata                          

  review_status              enum              UNREVIEWED / REVIEWED / DISMISSED YES
                                               / ESCALATED                       

  ai_generated               boolean           Whether narrative was generated   YES
                                               by AI                             

  ai_grounding_refs          array             Evidence refs supporting AI       YES if AI used
                                               narrative                         
  ------------------------------------------------------------------------------------------------

## Sheet: Research Gap Analysis

  -----------------------------------------------------------------------------------------------------------
  Area                Finding                          SENTRY Action            Priority       Source Basis
  ------------------- -------------------------------- ------------------------ -------------- --------------
  Indian procurement  DoE 2024/2025 manuals cover      Add rule families and    P0/P1          DoE manuals
  hierarchy           conflict of interest, supplier   detector applicability;                 
                      relationship management,         distinguish mandatory                   
                      debarment, cartel mitigation,    rules from good                         
                      tender design, bid evaluation,   practice.                               
                      contract management and risk                                             
                      mitigations.                                                             

  Specification /     Indian manual has dedicated need Add specification        P1             DoE Goods
  planning risk       assessment, technical            restriction,                            Manual 2024
                      specification and                over-tailoring, unusual                 
                      procurement-planning             qualification and                       
                      risk/mitigation material.        market-research anomaly                 
                                                       detectors.                              

  Evaluation          Procurement guidance addresses   Add evaluator/conflict   P1             DoE
  governance          subjective evaluation, committee data model where                        procurement
                      independence and conflicts of    lawful/public data                      guidance
                      interest.                        exists; otherwise                       
                                                       document/context checks.                

  Contract management Post-award guidance covers       Expand SENTRY beyond     P1             DoE Goods
                      amendments, delays, quality,     tender/award into                       Manual 2024
                      payment, disputes, closure,      post-award monitoring                   
                      reconciliation and               when data exists.                       
                      subcontractors/agents.                                                   

  Bidder withdrawal   Procurement guidance recognizes  Add withdrawal sequence  P0/P1          DoE
                      withdrawal after financial       and repeat-withdrawal                   procurement
                      opening / successful-bidder      patterns with                           manual
                      withdrawal as a                  legitimate-reason                       
                      supplier-performance/debarment   controls.                               
                      concern.                                                                 

  OECD detection list 2025 OECD list adds geographic   Map these into explicit  P0/P1          OECD 2025
                      allocation,                      pattern families; never                 
                      always-bid-never-win, incomplete treat one indicator as                  
                      bids, joint bids, identical      proof.                                  
                      errors/metadata, same submitter,                                         
                      synchronized submissions, shared                                         
                      addresses and subcontracting                                             
                      patterns.                                                                

  OCP                 73 indicators with formulas and  Use as reference         P0             OCP 2024
                      standardized data requirements;  catalogue and map by                    
                      lifecycle coverage from planning data availability; do                   
                      through implementation.          not blindly implement                   
                                                       all 73.                                 

  World Bank          Warning signs cover fraud,       Use as cross-check for   P1             World Bank
                      corruption, collusion and        broader integrity                       Integrity
                      coercion.                        categories.                             

  EU / Arachne        EU experience uses data mining,  Add document             P1/P2          European Court
                      risk indicators, semantic        semantics/cross-source                  of Auditors
                      analysis and abnormal-bidding    analytics as                            
                      checks alongside audits.         experimental until                      
                                                       Indian validation.                      

  Research:           Research supports close-loser    Add advanced statistical P2             Kawai / Imhof
  statistical screens absence, rotation/market         screening as                            research
                      division, bid                    P2/experimental.                        
                      variance/uniformity and                                                  
                      coalition screens.                                                       

  Research: network   Ownership + co-bidding temporal  Extend graph to          P1/P2          Network
  science             multiplex networks and           ownership/control and                   procurement
                      k-core/embeddedness can expose   co-bidding where                        research
                      network structures.              reliable public data                    
                                                       exists.                                 

  Missingness-aware   Recent research emphasizes       Keep missing data from   P2             2026 research
  ML                  uncertainty/missingness-aware    becoming risk; expose                   
                      graph learning and calibrated    uncertainty; consider ML                
                      risk.                            only after                              
                                                       labels/backtesting.                     

  TenderShield        Public project description       Use as coverage check;   P1             IIT Kanpur
                      covers specification rigging,    differentiate SENTRY                    project page
                      bid manipulation, evaluation     through provenance,                     
                      opacity, post-award fraud,       benchmarks, rule                        
                      vendor risk, audit trail and     authority and                           
                      whistleblower triage.            alternative                             
                                                       explanations.                           
  -----------------------------------------------------------------------------------------------------------

## Sheet: New Pattern Candidates

  -----------------------------------------------------------------------------------------------------------------
  Pattern ID  Pattern                Why Add                     Data Needed           Priority    Risk / Context
  ----------- ---------------------- --------------------------- --------------------- ----------- ----------------
  NEW-01      Always-bid-never-win   OECD explicitly identifies  supplier/tender       P0          Risk only with
                                     this as a warning sign;     participation +                   context
                                     useful cover-bid candidate. outcomes                          

  NEW-02      Regular bidder becomes OECD identifies expected    bid history +         P1          Risk/context
              subcontractor          bidder absence followed by  subcontract data                  
                                     subcontracting.                                               

  NEW-03      Winner subcontracts    OECD identifies this        award + subcontract   P1          Risk/context
              unsuccessful bidder    behaviour.                  data                              

  NEW-04      Geographic market      Repeated winner geography   supplier, buyer,      P0/P1       Risk signal
              allocation             partitions may indicate     geography, category,              
                                     allocation.                 time                              

  NEW-05      Same submitter /       Same person, author, IP or  bid metadata /        P1          Strong evidence
              document metadata      metadata can be a warning   submitter info                    only when
                                     sign where lawfully                                           authoritative
                                     available.                                                    

  NEW-06      Identical errors /     Repeated unique errors,     bid documents         P1          Document
              formatting fingerprint numbering or formatting can                                   evidence
                                     indicate common                                               
                                     preparation.                                                  

  NEW-07      Shared address /       Shared address alone is not public entity/address P1          Context;
              office network         misconduct but can          data                              corroboration
                                     strengthen a network                                          
                                     hypothesis.                                                   

  NEW-08      Repeated               Consistent                  bid responsiveness +  P1          Risk/context
              non-responsive bidder  incomplete/non-responsive   history                           
              cluster                bids can be a cover-bid                                       
                                     candidate.                                                    

  NEW-09      Submission-time        Very close/synchronized     submission timestamps P1          Risk/context
              clustering             submissions across rivals                                     
                                     are an OECD warning sign.                                     

  NEW-10      Backlog-adjusted       Capacity/backlog can help   award history +       P2          Research screen
              rotation               distinguish legitimate      values + time                     
                                     rotation from suspicious                                      
                                     rotation.                                                     

  NEW-11      Close-loser missing    Absence of close losing     bid values/ranks      P2          Statistical
              mass                   bids can be informative in                                    screen
                                     collusion screening.                                          

  NEW-12      Coalition bid          Group-level screens can     bid values + bidder   P2          ML/statistical
              variance/uniformity    identify coordinated bidder groups                            
                                     coalitions.                                                   

  NEW-13      Ownership × co-bidding Corporate ownership links   ownership/control +   P2          Context/risk
              network                plus repeated co-bidding    bids                              
                                     strengthen network context.                                   

  NEW-14      Post-award amendment   Material scope/value        contract amendments + P1          Post-award risk
              advantage              changes may alter the       award                             
                                     economics of the original                                     
                                     award.                                                        

  NEW-15      Performance/payment    Payments inconsistent with  invoice, delivery,    P1/P2       Post-award risk
              mismatch               verified                    inspection, payment               
                                     delivery/performance                                          
                                     indicate execution risk.                                      

  NEW-16      Unclosed contract /    Persistent                  closure, payment,     P2          Context/risk
              unreconciled assets    closure/reconciliation gaps asset, security                   
                                     are operational integrity   records                           
                                     signals.                                                      
  -----------------------------------------------------------------------------------------------------------------

## Sheet: Source Authority Map

  -------------------------------------------------------------------------------------------------
  Source         Authority Tier     Use In SENTRY             Do Not Do              Refresh
  -------------- ------------------ ------------------------- ---------------------- --------------
  DoE / GFR /    A --- Indian       Rules, applicability,     Do not turn every      Monitor
  Manuals        authoritative      exceptions, debarment,    recommendation into a  amendments
                                    tender/contract process   legal violation        

  CPPP /         A --- primary      Tender, corrigendum,      Do not infer           Continuous
  eProcure       procurement data   award metadata/documents  nationwide             
                                    where published           completeness           

  CCI            A --- competition  Bid-rigging/cartel        Do not label an entity Continuous
                 authority          concepts, enforcement     guilty from a mere     
                                    cases, advocacy           mention/allegation     

  GeM            A --- platform     GeM-specific procurement  Do not generalize      Continuous
                 primary            events and rules where    GeM-specific rules to  
                                    accessible                all procurement        

  CVC            A --- vigilance    Applicable                Do not turn general    Monitor
                 authority          vigilance/procurement     advice into universal  updates
                                    integrity guidance        law                    

  OECD           B ---              Bid-rigging indicators    Do not treat as Indian Versioned
                 international      and tender-design         law                    
                 methodology        principles                                       

  OCP            B --- methodology  73 red flags, formulas,   Do not blindly deploy  Versioned
                                    OCDS mapping              all indicators         

  World Bank     B --- methodology  Fraud/corruption warning  Do not treat as Indian Versioned
                                    signs                     legal authority        

  EU / ECA /     B ---              Fraud-risk analytics,     Do not assume EU rules Versioned
  OLAF           methodology/case   semantic/document ideas   apply in India         
                 practice                                                            

  Academic       C --- research     Advanced                  Do not productionize   Versioned
  research       evidence           statistical/network/ML    without validation     
                                    screens                                          

  News           D --- contextual   External event            Never treat            Continuous
                 evidence           discovery/corroboration   sentiment/allegation   
                                                              as proof               
  -------------------------------------------------------------------------------------------------

## Sheet: Do Not Score Context

  -------------------------------------------------------------------------------------
  Signal            Default Treatment Reason                      What Can Upgrade It
  ----------------- ----------------- --------------------------- ---------------------
  News allegation   Context only      Allegation is not a         Primary official
                                      finding; source             record + relevant
                                      quality/status matter       verified status

  Old court/CCI     Context until     Case stage and relevance    Verified
  mention           status verified   matter                      order/status +
                                                                  identity/date/scope

  Shared address    Context           May be legitimate           Multiple independent
                                      office/service address      network signals

  Same director     Context           Corporate relationships can Relevant
                                      be legitimate               control/ownership +
                                                                  procurement pattern

  Single bidder     Contextual risk   Specialized/emergency       Strong benchmark
                    signal            markets can legitimately    deviation + process
                                      have one bidder             context

  High win rate     Contextual risk   Incumbency/specialization   Comparable-market
                    signal            can explain concentration   abnormality +
                                                                  corroboration

  Similar prices    Contextual risk   Regulated/catalog pricing   Repeated abnormality
                    signal            can create similarity       after controls +
                                                                  other evidence

  Missing data      Never positive    Missingness is an           None; only confidence
                    risk              uncertainty problem         changes

  AI inference      Never             AI can hallucinate or       Must be grounded and
                    source-of-truth   overstate                   marked inference
  -------------------------------------------------------------------------------------


---

# APPENDED: SENTRY INTELLIGENCE GAP ANALYSIS

# SENTRY --- Intelligence Gap Analysis

## Executive conclusion

Deep research does **not** require replacing SENTRY's architecture. It
shows where the system should become more complete:

1.  Deepen the Indian procurement rule layer.
2.  Cover the entire procurement lifecycle, not only tender/award.
3.  Enrich the ecosystem graph with co-bidding, ownership/control,
    subcontracting and post-award relationships.
4.  Keep advanced statistical/ML screening separate from authoritative
    rules.
5.  Treat missingness and uncertainty as first-class concepts.
6.  Treat news as context/corroboration, never as raw proof.
7.  Use TenderShield and similar systems as coverage references, not as
    SENTRY's source of truth.

------------------------------------------------------------------------

# 1. Indian Procurement

The Department of Expenditure's current manual catalogue includes the
Goods Manual (Second Edition, 2024), Works Manual (Second Edition,
2025), Consultancy Services Manual (Second Edition, 2025), and
Non-Consultancy Services Manual (2025).

The Goods Manual covers procurement principles, specifications/planning,
supplier relationship management, Code of Integrity, Integrity Pact,
grievances, debarment, tendering, bid evaluation, award, contract
management and risk mitigations.

The 2024 Goods Manual specifically highlights **conflict of interest,
auto-extension of bids, price-variation/liquidated-damages controls,
mitigating cartel formation, reverse auction, rate contracts, withdrawal
by L1 bidders, NPV and disaster procurement** among the areas revised.

### SENTRY implication

These topics should become explicit Rule Registry families rather than
being buried as generic documentation.

------------------------------------------------------------------------

# 2. CPPP / eProcurement

CPPP describes itself as a central access point for procurement
information and states that covered organizations publish tender
enquiries, corrigenda and award details.

Therefore SENTRY should preserve:

``` text
Tender
  ↓
Corrigendum events
  ↓
Deadline changes
  ↓
Bid opening
  ↓
Award
```

A corrigendum should never overwrite the original tender. It is a
timeline event and can become evidence for change-point and process
analysis.

------------------------------------------------------------------------

# 3. CCI / Competition

CCI publicly maintains bid-rigging/cartel advocacy material and has
enforcement cases involving public-procurement bid rigging, including
cases concerning the Department of Printing and Eastern Railway.

SENTRY should maintain a **Competition / Enforcement Context** layer.

Critical distinction:

``` text
CCI case exists
        ≠
entity is guilty

verified order/status
+
exact entity
+
relevant tender/time
        =
usable contextual evidence
```

------------------------------------------------------------------------

# 4. OECD 2025 Detection List

The 2025 OECD detection list adds important pattern coverage.

### Bidding patterns

-   frequent same-supplier success
-   geographic allocation
-   expected bidders not bidding and later subcontracting
-   repeated withdrawals
-   always-bid-never-win firms
-   taking turns winning
-   joint bids between firms that previously competed independently
-   repeated incomplete/non-responsive bids

### Tender documents

-   identical errors
-   identical/similar formatting or metadata
-   same IP/document author where lawfully available
-   same person submitting competing bids
-   competitor details appearing in another bid
-   repeated incomplete bids
-   identical item estimates or ancillary terms
-   matching adjustments
-   suspiciously incomplete detail
-   synchronized submissions
-   repeated submission sequence
-   shared address/office/financial relationships

### Behaviour

-   statements referring to agreements
-   industry price schedules
-   territory/customer allocation
-   advance knowledge of competitors' pricing/results
-   cover-bid references
-   common explanations
-   trade-association discussions
-   supplier meetings
-   shared consultants
-   winner subcontracting unsuccessful bidders

**Important:** OECD explicitly cautions that indicators are not proof. A
suspicious pattern can have legitimate explanations, and historical
patterns over time are generally more informative than a single tender.

------------------------------------------------------------------------

# 5. OCP --- 73 Red Flags

OCP's 2024 guide provides 73 public-procurement indicators with
definitions, formulas, examples and standardized-data requirements
mapped to OCDS.

SENTRY should treat OCP as a **reference catalogue**.

For every indicator:

``` text
OCP indicator
    ↓
Required fields available?
    ↓
Applicable in Indian procurement?
    ↓
Duplicate of existing detector?
    ↓
Benchmark possible?
    ↓
Legitimate explanations testable?
    ↓
P0 / P1 / P2 / Research-only / Reject
```

This is better than blindly implementing all 73.

------------------------------------------------------------------------

# 6. World Bank

World Bank Integrity materials cover warning signs for fraud,
corruption, collusion and coercion.

Use them to cross-check broader procurement-integrity categories.

They are methodology/context, not Indian legal authority.

------------------------------------------------------------------------

# 7. EU / Arachne Lessons

EU audit material documents the use of:

-   fraud-risk indicators
-   data mining
-   semantic analysis of bids
-   abnormal bidding patterns
-   conflict-of-interest checks
-   double-claim detection
-   collaboration with procurement/competition authorities

The important lesson is:

``` text
Analytics + verification + audit
```

not analytics replacing verification.

------------------------------------------------------------------------

# 8. TenderShield Coverage Check

The public TenderShield project description includes:

-   specification rigging
-   bid manipulation
-   evaluation opacity
-   post-award fraud
-   unreviewed evidence
-   anomaly detection
-   identical pricing
-   rotation
-   suspicious withdrawals
-   vendor risk
-   litigation/compliance/performance history
-   decision audit trail
-   whistleblower triage

This validates several SENTRY directions.

SENTRY should differentiate itself through:

``` text
Contextual benchmarks
+
Authority-aware rules
+
Longitudinal entity history
+
Heterogeneous ecosystem graph
+
Evidence provenance
+
Alternative explanations
+
Missingness/uncertainty
+
Investigator-first explanations
```

------------------------------------------------------------------------

# 9. New Patterns to Add

## P0/P1

1.  Always-bid-never-win
2.  Geographic market allocation
3.  Repeated non-responsive bidder clusters
4.  Winner/loser rotation
5.  Bid withdrawal sequences
6.  Repeated bidder submission sequence
7.  Synchronized bid submission
8.  Identical/near-identical bid pricing
9.  Identical errors / document fingerprints
10. Repeated shared metadata
11. Specification restriction / over-tailoring
12. Qualification/eligibility anomaly
13. Active eligibility/debarment
14. Material post-award amendment
15. Winner subcontracting unsuccessful bidder
16. Expected bidder becoming subcontractor
17. Supplier concentration
18. Buyer-supplier concentration

## P2 / Research

19. Close-loser missing mass
20. Backlog-adjusted rotation
21. Coalition-level bid screens
22. Bid variance/uniformity
23. Ownership × co-bidding multiplex network
24. k-core/network embeddedness
25. Supplier behaviour change-point detection
26. Missingness-aware graph learning

------------------------------------------------------------------------

# 10. Post-Award Gap

One of the biggest opportunities is to extend SENTRY beyond:

``` text
Tender → Winner
```

toward:

``` text
Tender
 ↓
Award
 ↓
Contract
 ↓
Amendment
 ↓
Delivery
 ↓
Inspection
 ↓
Invoice
 ↓
Payment
 ↓
Performance
 ↓
Closure
```

Indian procurement guidance explicitly addresses contract amendments,
performance, delays, quality, payments, disputes, termination, closure,
reconciliation and subcontractors/agents.

Therefore post-award intelligence should be P1/P2.

### Candidate post-award detectors

**Amendment advantage**

Compare:

``` text
Original scope vs amended scope
Original value vs amended value
Original timeline vs amended timeline
```

Do not flag every amendment.

**Performance/payment mismatch**

Where data exists:

``` text
invoice
vs delivery
vs inspection
vs payment
```

**Contract closure anomaly**

Examples:

-   final payment but unresolved closure
-   unreconciled recoveries
-   unresolved securities
-   unresolved assets/materials

------------------------------------------------------------------------

# 11. Advanced Statistical Research

Recent research supports several advanced screens.

### Close-loser / missing-mass

The absence of close losing bids can be informative in collusion
screening.

### Designated-winner persistence

Repeated persistence of a winner across rebid rounds can be informative.

### Rotation vs legitimate capacity

Rotation can arise legitimately because firms have different
capacity/backlog. Advanced screening should therefore compare rotation
with firm backlog/availability rather than assuming rotation equals
collusion.

### Coalition-level screening

Instead of only scoring a tender, examine bidder groups using variance,
uniformity and repeated coalition behaviour.

### Network embeddedness

Ownership/control links combined with co-bidding and temporal network
structure can strengthen ecosystem analysis.

These should be **P2/research-first**, not simplistic production rules.

------------------------------------------------------------------------

# 12. News Intelligence

News should remain external context.

Recommended architecture:

``` text
Tender / Supplier / Buyer
        ↓
Query Generator
        ↓
Search / News Provider
        ↓
Candidate Articles
        ↓
Deduplication
        ↓
Entity Resolution
        ↓
Tender/Project Matching
        ↓
Event Extraction
        ↓
Source Quality
        ↓
Official Corroboration
        ↓
Evidence Store
```

Query families:

``` text
"<supplier>" tender
"<supplier>" procurement
"<supplier>" contract
"<supplier>" debarment
"<supplier>" CCI
"<supplier>" court
"<supplier>" investigation

"<buyer>" "<project>"
"<tender ID>"
"<tender title>"
```

Every external event should have status:

``` text
allegation
investigation
charge
proceeding
order
judgment
dismissed
acquitted
settled
resolved
unknown
```

Never collapse all of these into "bad history".

------------------------------------------------------------------------

# 13. What Should NOT Be Scored Directly

Keep these as context unless independently corroborated:

-   news allegations
-   generic negative sentiment
-   old case mentions with unknown status
-   shared address alone
-   shared director alone
-   high win rate alone
-   one bidder alone
-   similar prices alone
-   missing data
-   AI speculation
-   arbitrary global thresholds

Missingness should normally **reduce confidence**, not increase risk.

------------------------------------------------------------------------

# 14. Benchmark Upgrade

The research reinforces one major principle:

> **Better benchmarking is more valuable than simply adding more red
> flags.**

Prefer comparison populations defined by:

``` text
buyer
+
category
+
procurement method
+
geography
+
value band
+
time
```

Prefer:

-   median
-   percentile
-   IQR
-   distribution
-   historical baseline
-   peer baseline

Every benchmark must preserve its population definition and calculation
method.

------------------------------------------------------------------------

# 15. Evidence Convergence

Do not count correlated signals independently.

Bad:

``` text
price gap
price ratio
price spread
price similarity
= 4 independent red flags
```

They may all derive from the same bid values.

Better:

``` text
Competition family
Pricing family
Participation family
Network family
Document family
Official-context family
```

Cross-family convergence is more informative than duplicated
measurements from one underlying variable.

------------------------------------------------------------------------

# 16. Final Research-Driven SENTRY Architecture

``` text
INDIAN AUTHORITATIVE RULES
          |
          +---- GFR / DoE / applicable rules
          +---- CCI / competition context
          +---- CPPP / GeM platform rules
          |
          v
PROCUREMENT DATA
          |
          v
NORMALIZATION
          |
          v
ENTITY RESOLUTION
          |
          +------------------+
          |                  |
          v                  v
BENCHMARK ENGINE       ECOSYSTEM GRAPH
          |                  |
          +--------+---------+
                   |
                   v
             PATTERN ENGINE
                   |
       +-----------+-----------+
       |           |           |
       v           v           v
 Competition    Pricing     Process
       |           |           |
       +-----------+-----------+
                   |
                   v
             POST-AWARD
                   |
                   v
         EXTERNAL CONTEXT
        /                 \
 Official records        News
        \                 /
         +-------+-------+
                 |
                 v
           EVIDENCE LAYER
                 |
                 v
       ALTERNATIVE EXPLANATIONS
                 |
                 v
        EVIDENCE CONVERGENCE
                 |
                 v
          RISK PRIORITIZATION
                 |
                 v
        INVESTIGATOR WORKBENCH
```

------------------------------------------------------------------------

# 17. Final Research Decision

### Keep

-   Rule Registry
-   Red-Flag Registry
-   Benchmark Registry
-   existing pattern library
-   ecosystem model
-   entity resolution
-   evidence architecture
-   P0 detector framework

### Upgrade

-   specification/planning rules
-   conflict-of-interest model
-   withdrawal patterns
-   always-bid-never-win
-   geographic allocation
-   document/metadata fingerprints
-   synchronized submissions
-   subcontracting relationships
-   post-award lifecycle
-   ownership × co-bidding graph
-   missingness/uncertainty
-   evidence-family convergence

### Research-only / P2

-   coalition ML
-   close-loser missing mass
-   backlog-adjusted rotation
-   k-core/network ML
-   missingness-aware graph transformers

### Do not score directly

-   news allegations
-   generic reputation
-   shared address
-   shared director
-   missing data
-   AI speculation

------------------------------------------------------------------------

# 18. Bottom Line

The research strengthens the original SENTRY idea.

The biggest upgrade is **not more AI**.

It is:

> **SENTRY should become a longitudinal, evidence-backed procurement
> intelligence graph combining authoritative Indian procurement rules,
> contextual benchmarks, bid/price/participation patterns, entity
> relationships, post-award behaviour and verified external context.**

That is substantially more defensible than a simple red-flag dashboard.
