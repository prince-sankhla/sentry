# GePNIC Connector Audit — Odisha (`eproc_odisha`)

**Scope:** Audit of the GePNIC connector only. No engine changes, no new typologies, no
implementation. Objective: determine whether Odisha GePNIC exposes primary procurement
documents, whether our connector fails to retrieve them, and — if it is a bug — the exact
cause and the smallest fix.

**Verdict:** The portal **does** expose primary documents. The connector **does** fail to
surface them. The failure is a **scraper (connector) bug, not a portal limitation.** The
document links are already present in HTML we have downloaded and stored on disk — the
pipeline simply never extracts them.

---

## 1. Does Odisha GePNIC expose primary procurement documents? — YES

Odisha runs standard NIC GePNIC (Apache Tapestry) at `https://tendersodisha.gov.in`
(portal registered in [portals.py:30](backend/app/connectors/state_eproc/portals.py#L30)).

Evidence, taken directly from our own stored raw record
[2026_CERWI_133303_1.json](data/raw/eproc_odisha/2026_CERWI_133303_1.json) — the
`data.detail_html` field contains the public **FrontEndTenderDetails** page, which includes:

- Section labels: `NIT Document`, `Work Item Documents`, `BOQ`, `Download as zip`
- Real primary-document filenames:
  - `Tendernotice_1.pdf`, `Tendernotice_2.pdf`, `Tendernotice_3.pdf` — NIT / tender notice
  - `tDTCN01.pdf` — Detailed Tender Call Notice
  - `tNCB1.pdf` — BoQ / NCB work-item document
  - `tCorrigendum1.pdf` — Corrigendum
- Download anchors (Tapestry component links):
  ```
  <a id="docDownoad"   href="/nicgep/app?component=docDownoad&page=FrontEndTenderDetails&service=direct&session=T">
  <a id="docDownoad_0" href="/nicgep/app?component=docDownoad&page=FrontEndTenderDetails&service=direct&session=T">
  <a id="docDownoad_1" href="/nicgep/app?component=docDownoad&page=FrontEndTenderDetails&service=direct&session=T">
  ```

This is **not** an isolated record: **all 28** stored Odisha raw files contain document
references (`docDownoad` / `NIT Document` / `Work Item Documents` / `.pdf`). Document
exposure is universal for this portal.

---

## 2. Investigation checklist

| # | Item | Finding |
|---|------|---------|
| 1 | **HTML structure** | Detail page is NIC `FrontEndTenderDetails`, standard `td_caption`/`td_field` table plus a documents section with `docDownoad*` anchors and `.pdf` filenames. We already fetch and store this full HTML. |
| 2 | **PDF links** | Present in the stored HTML as real filenames + download anchors. Not missing from the source. |
| 3 | **Hidden endpoints** | None required. Documents are served by the same `/nicgep/app` Tapestry endpoint via the `docDownoad` component. No separate/undocumented API involved. |
| 4 | **Session requirements** | The `docDownoad` links are **stateful Tapestry links** — `...&session=T` with **no `sp=` serialized state**. The document is resolved server-side from the live session/page state, keyed only by the anchor `id`. The detail-page **HTML** is public and needs no login; fetching the **PDF bytes** requires hitting the link inside the *same* session that rendered the page. |
| 5 | **Cookies** | The existing `httpx.Client` (single session per crawl, [downloader.py:61](backend/app/connectors/cppp/downloader.py#L61)) already carries the JSESSIONID cookie across list→detail requests. No cookie problem for the HTML; a document fetch would just need to reuse that same client before it closes. |
| 6 | **JavaScript rendering** | Not required. Documents and links are server-rendered into the HTML we already capture. No headless browser needed. |
| 7 | **CAPTCHA / anti-bot** | None encountered on the public list/detail/document path. (GePNIC CAPTCHA appears only on bidder login / bid submission, which we do not touch.) |
| 8 | **Download URLs** | Recoverable from stored HTML (anchor href + adjacent filename + section label). URLs are session-relative (see #4), so they identify documents but cannot be re-fetched "cold" months later. |
| 9 | **Bug or portal limitation?** | **Scraper bug.** The documents are exposed and already sitting in our on-disk HTML; nothing in the pipeline extracts them. |

---

## 3. Root cause (confirmed)

The connector retrieves the detail HTML successfully. The document links inside it are then
dropped at **two** points, neither of which touches the documents section:

1. **Persistence layer — `_save_record` never populates the envelope's `documents` list.**
   Both [cppp/downloader.py:134](backend/app/connectors/cppp/downloader.py#L134) and the
   Odisha override [state_eproc/downloader.py:18](backend/app/connectors/state_eproc/downloader.py#L18)
   call `build_envelope(... data={"detail_html": ...})` **without a `documents=` argument.**
   `build_envelope` defaults it to `[]` ([envelope.py:57](backend/app/connectors/common/envelope.py#L57)).
   Contrast with connectors that do it correctly, e.g.
   [cag/downloader.py:60](backend/app/connectors/cag/downloader.py#L60) and
   [datagovin/downloader.py:80](backend/app/connectors/datagovin/downloader.py#L80),
   which pass `documents=[...]`. The NIC downloader simply omits this.

2. **Mapping layer — `map_notice` parses only caption fields, never document anchors.**
   [cppp/mapper.py:134 `_extract_label_values`](backend/app/connectors/cppp/mapper.py#L134)
   scans `td_caption`/`td_field` pairs for Tender ID / title / dates / value only. It has no
   awareness of the `docDownoad` anchors or `.pdf` filenames.

Consequently, `documents_from_envelope`
([envelope.py:88](backend/app/connectors/common/envelope.py#L88)) reads
`raw_record["documents"]` (empty) and yields **only** the single "Source notice" URL. The
NIT, BoQ, DTCN and Corrigendum PDFs are never turned into `NormalizedDocument` entries.

The plumbing to carry documents already exists end-to-end (`build_envelope(documents=…)` →
envelope `documents[]` → `documents_from_envelope`). **Nothing populates it for NIC.** That is
the whole bug. The `docDownoad` component string appears **nowhere** in the codebase — only in
the raw data — confirming no extractor was ever written.

---

## 4. Smallest possible fix (proposed — not implemented)

One small, additive change; no architecture change, no engine change, no new typology.

**Add a NIC document-anchor extractor and feed the existing `documents=` channel.**

- Write one helper, e.g. `_extract_nic_documents(detail_html) -> list[dict]`, that walks the
  documents section and returns `{"title": <filename>, "url": <urljoin(base, href)>,
  "document_type": <"nit"|"boq"|"corrigendum"|"work_item"|"attachment" from the section label>}`.
  Reuse the existing `_LinkParser`/regex style already in
  [cppp/downloader.py](backend/app/connectors/cppp/downloader.py) — no new dependency.
- Call it in `_save_record` and pass the result as `documents=` to `build_envelope`
  (in both the CPPP and `StateEProcDownloader` overrides). This is exactly the pattern CAG /
  datagovin already use.

That is the minimal change. Two clarifications so scope stays honest:

- **This surfaces document identity + URL + type.** Because those numbers already flow through
  `documents_from_envelope`, the documents will appear on normalized records with **no** change
  to the mapper, engine, or schema.
- **Recovering the 28 already-downloaded records:** the fix above only affects *new* crawls. To
  recover existing files without re-scraping, the same helper can instead (or also) be invoked
  inside `documents_from_envelope` as a fallback when `raw_record["documents"]` is empty —
  parsing `raw_record["data"]["detail_html"]`. This reads the documents we already have on disk.
  Pick one placement; both reuse the same one helper.
- **Downloading the PDF bytes** (as opposed to their URLs) is a *separate, larger* effort
  because the `docDownoad` links are session-stateful (§2/#4) and must be fetched inside the
  live crawl session. It is out of scope for "surface the documents" and should not be bundled
  into this fix.

**Recommendation:** implement `_extract_nic_documents` once and wire it in
`documents_from_envelope` as the empty-list fallback — a single helper that both fixes new
crawls and recovers all 28 existing Odisha records with zero re-scraping and no engine impact.

---

## 5. Answer to the two framing questions

- *Does Odisha GePNIC expose primary procurement documents?* **Yes** — NIT, BoQ (NCB),
  DTCN, Corrigendum, "Download as zip", on the public detail page, in every sampled record.
- *Does our connector fail to retrieve them?* **Yes — but it is a bug, not a portal wall.**
  We already download and store the HTML containing the links; the pipeline never extracts
  them into the `documents` channel that exists precisely for this purpose.
