# GePNIC Document Linking — Technical Recommendation

**Status:** Recommendation only. Nothing implemented. No portal circumvention proposed.
**Question:** GePNIC document download URLs are session-dependent. What is the most
*technically honest* way for SENTRY to cite/serve primary procurement documents?

**Bottom line:** Do **not** treat the raw GePNIC download URL as evidence — it is
structurally ephemeral and will break on click. The honest, long-term-correct model is the
one every serious investigation platform uses: **cite a stable official handle (the Tender
ID / tender-details page) now, and archive the document bytes into SENTRY's own preservation
store later.** SENTRY should link to the **official tender record**, display the document
*manifest* as proof-of-existence, and be explicit that binaries are *referenced*, not
hotlinked — until we archive them ourselves.

---

## 1. Can GePNIC generate permanent document URLs? — **No (not through its public interface).**

Confirmed from the URL structure in our own stored records and from Apache Tapestry's own
documentation (GePNIC runs on Apache Tapestry):

- The document links we captured are Tapestry **DirectLink** actions:
  `/nicgep/app?component=docDownoad&…&session=T` (NIT docs) and
  `…component=%24DirectLink_9&…&session=T&sp=<gzip+base64 state>` (BoQ / work-item docs).
- The `session=T` parameter is not incidental — Tapestry adds it **specifically so it can
  detect an expired session and raise a "stale link" error.** Per the Tapestry docs and
  community, *"a DirectLink is always relative to an existing session… that will always be
  the case, it's the nature of a DirectLink."* For a session-independent link Tapestry tells
  you to use a different component (ExternalLink) entirely — which GePNIC does **not** use for
  documents.
- The `sp=` token is **serialized page/listener state** (client persistence). It is bound to
  the render cycle and is explicitly documented as fragile (URL bloat, truncation, tied to the
  request). The `docDownoad` NIT links carry **no `sp` at all** — they are *purely* session-bound.

So the download URL is an ephemeral RPC handle, not an address. There is no stable, public,
dereferenceable document URL, and no public document REST/OCDS API on the state GePNIC portals.

**Important corollary:** the URL SENTRY currently stores as the "Source notice"
(`…component=%24DirectLink&page=FrontEndListTendersbyDate&…&session=T&sp=…`) is **itself a
session-scoped DirectLink** — it is *also* not permanent. The only durable public handle is
the **Tender ID** (e.g. `2026_ORULB_132524_2`), which the portal's public tender search
resolves. That is the citation key we should anchor on. (The exact canonical search/permalink
format should be confirmed from NIC documentation — not by probing the portal.)

## 2. Why permanent URLs are not available

Three independent reasons, all structural — not a bug we can fix from the outside:

1. **Framework:** Tapestry's stateful component model addresses a download as a server-side
   *listener action* keyed to the `JSESSIONID` + page state, not a static file path.
2. **Deliberate access design:** NIC routes every download through the application so it can
   enforce session validity, throttling, audit logging, and (for some document classes)
   login/DSC gating. There is no CDN/object-store with public permalinks by design.
3. **No open data layer:** unlike OCDS publishers, state GePNIC portals expose no document API
   and mint no persistent document identifiers.

Nothing SENTRY can do — short of circumventing the session model, which we will not do — turns
these into permanent URLs.

## 3. Industry best practice for procurement-investigation platforms

The consensus across open-contracting and investigative-journalism tooling is **"capture and
preserve, don't hotlink"**:

- **Open Contracting Data Standard (OCDS):** models each document as a structured object
  (`id`, `documentType` from a controlled codelist — `tenderNotice`, `biddingDocuments`,
  `awardNotice`, … — `title`, `format`, `datePublished`, `url`) and **strongly emphasises
  persistent URIs**; the UK OCDS profile goes further and recommends **archiving the linked
  documents to PDF/A** so the reference survives. Takeaway: structured document metadata +
  a *stable* URL + your own archived copy.
- **OCCRP Aleph:** keeps the **original files** in a dedicated file archive (S3/GCS/FS),
  ingests them, and preserves provenance per-origin. Aleph exists precisely to *hold the
  primary documents*, not to point at someone else's ephemeral link.
- **General evidentiary principle:** the citation of record must not rot. A link that 500s or
  "stale-sessions" on click has zero evidentiary value and actively misleads.

## 4. Should SENTRY link to the document, or to the official tender-details page?

**Link to the official tender record (by Tender ID), and treat the document as an archived
artifact — not a hotlink.** Concretely, three layers, in priority order:

1. **Primary citation → the official tender-details page, addressed by the stable Tender ID.**
   This is the human-navigable government record an investigator/journalist can independently
   reach and verify. It is the honest "official source."
2. **Document manifest → display identity + type (+ size/date) as proof the document exists**
   and is officially listed (NIT, BoQ, Corrigendum, …). We already recover this. It is
   truthful evidence-of-existence even before we hold the bytes.
3. **Document bytes → serve SENTRY's *own archived copy* (once captured), with provenance.**
   The archived copy — not the portal's session URL — becomes the durable, clickable evidence.

**Do not** render the raw `docDownoad`/`sp` URL as a working "Download" button. It looks like
evidence and breaks on click — the opposite of technically honest.

## 5. What Palantir / OCCRP Aleph / Open Contracting Partnership would likely do

| Actor | Likely approach | Common thread |
|---|---|---|
| **OCCRP Aleph** | Ingest the PDF/BoQ into its **file archive**, index it, keep provenance (source + retrieval). Holds the artifact itself. | Capture the bytes |
| **Open Contracting Partnership / OCDS** | Emit a structured `documents` array (codelist `documentType`, `format`, `datePublished`), push for **persistent URIs**, and **archive to PDF/A** where the source can't guarantee persistence. | Structure + persist + archive |
| **Palantir (Foundry/Gotham)** | Ingest the artifact as an object with full **lineage** back to source; never make live evidence depend on a third-party stateful URL. | Provenance-first ingest |

All three converge: **the platform holds a preserved copy and records provenance; the
third-party URL is a provenance pointer, never the evidence.** None would ship a session-bound
hotlink as the document citation.

## 6. Recommended smallest implementation (correct · defensible · demo-ideal)

Two phases. Phase 1 is tiny and is the honest, demo-ready state. Phase 2 is the long-term-correct
finish and — critically — **layers on with no architecture change** (the envelope already
reserves `documents[]` and a preservation layer).

**Phase 1 — Honest provenance display (small; no new infra, no byte download):**
- Keep the recovered manifest (title + type — already done). Map `document_type` to the **OCDS
  `documentType` codelist** (`nit`→`tenderNotice`/`biddingDocuments`, `boq`→`biddingDocuments`,
  `corrigendum`→`tenderChanges`) so it is standards-aligned.
- Render each document as **"Official document listed on the portal"** with the primary link
  pointing at the **tender-details page by Tender ID**, labelled honestly (e.g. *"Verify on
  tendersodisha.gov.in"*). Mark binaries **"identified · not yet archived."**
- **Stop** surfacing the session-scoped `docDownoad`/`sp` URL as a clickable download.
- This *is* the "red-flag → official government record in one click" demo — done truthfully.

**Phase 2 — Crawl-time archival (later; the correct long-term layer):**
- During the crawl, **within the same live session**, fetch the **publicly downloadable**
  document bytes (only docs served without login/DSC — no circumvention), store them
  content-addressed (hash) in SENTRY's preservation store, ideally normalised to **PDF/A**.
- Cite the **archived copy** as the durable evidence *alongside* the official tender page.
- Because the envelope already carries `documents[]` and provenance, this needs **no redesign**.

### Why this is the right call

- **Technically correct:** it never depends on an ephemeral URL as evidence, matching how
  Aleph/Palantir/OCDS treat primary documents.
- **Legally defensible:** deep-linking public government records and displaying lawfully
  retrieved public metadata are clearly lawful; we perform **no session circumvention**, so
  there is no unauthorized-access exposure. Phase 2 archives **only** publicly accessible
  documents, with provenance — standard public-interest practice. (Recommend a quick NIC
  ToS/robots review before any *bulk* archival.)
- **Demo-ideal:** the investigator clicks through from a SENTRY red flag to the **official
  government tender record** and sees the exact document manifest (NIT, BoQ) that substantiates
  it — persuasive *and* honest, with zero risk of a dead/stale link on stage.

---

### Sources
- [Apache Tapestry — Stale Links and the Browser Back Button](https://tapestry.apache.org/tapestry3/doc/DevelopersGuide/pages.stale-links.html)
- [Apache Tapestry — DirectLink](https://tapestry.apache.org/tapestry4.1/quickstart/directlink.html)
- [Apache Tapestry — Persistent Page Data (client vs. session persistence)](https://tapestry.apache.org/persistent-page-data.html)
- [OCDS — Release Reference (documents / documentType)](https://standard.open-contracting.org/latest/en/schema/reference/)
- [OCDS — How data is published (persistent URLs)](https://standard.open-contracting.org/latest/en/primer/releases_and_records/)
- [UK Government OCDS profile (permanent URIs + PDF/A archival)](https://www.gov.uk/government/publications/open-standards-for-government/open-contracting-data-standard-profile)
- [Aleph — Architecture Overview (file archive)](https://docs.aleph.occrp.org/developers/explanation/architecture/)
- [Aleph — Ingest Pipeline (original-file preservation + provenance)](https://docs.aleph.occrp.org/developers/explanation/ingest-pipeline/)
