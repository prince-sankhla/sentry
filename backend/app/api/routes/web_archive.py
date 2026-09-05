from __future__ import annotations

import html
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.webintel.models import WebEvidence

router = APIRouter(prefix="/api/web", tags=["web-intelligence"])


@router.get("/archive/{evidence_id}", response_class=HTMLResponse)
def archive_web_evidence(evidence_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render an immutable SENTRY-captured web snapshot.

    The snapshot is served from the database rather than the source site, so a
    source-session expiry, login wall, redirect, or later page change does not
    break the investigator's review trail.
    """
    evidence = db.scalar(select(WebEvidence).where(WebEvidence.id == evidence_id))
    if evidence is None:
        raise HTTPException(status_code=404, detail="Stored web snapshot not found.")

    title = html.escape(evidence.title or "SENTRY web snapshot")
    source = html.escape(evidence.source or "Unknown source")
    original_url = html.escape(evidence.url, quote=True)
    retrieved = html.escape(evidence.retrieved_at.isoformat())
    content_hash = html.escape(evidence.content_hash)
    content = html.escape(evidence.content)

    document = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>SENTRY Snapshot · {title}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0a0b0d; --panel:#111318; --line:#272b33; --text:#e8eaed; --muted:#949aa5; --accent:#8bf7c7; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.65 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif; }}
    main {{ max-width:1080px; margin:0 auto; padding:48px 24px 72px; }}
    .eyebrow {{ color:var(--accent); font-size:11px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ margin:10px 0 8px; font-size:30px; line-height:1.15; letter-spacing:-.025em; }}
    .meta {{ color:var(--muted); font-size:12px; }} .panel {{ margin-top:24px; border:1px solid var(--line); border-radius:16px; background:var(--panel); overflow:hidden; }}
    .bar {{ display:flex; flex-wrap:wrap; gap:14px 22px; padding:16px 18px; border-bottom:1px solid var(--line); color:var(--muted); font-size:12px; }}
    .bar strong {{ color:var(--text); font-weight:600; }} a {{ color:var(--accent); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
    pre {{ margin:0; padding:22px; white-space:pre-wrap; overflow-wrap:anywhere; font:12px/1.75 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:#d8dbe0; }}
    .note {{ margin-top:16px; color:var(--muted); font-size:11px; }}
  </style>
</head>
<body>
  <main>
    <div class=\"eyebrow\">SENTRY · Captured source snapshot</div>
    <h1>{title}</h1>
    <div class=\"meta\">Stable review copy served by SENTRY — independent of the current state of the original website.</div>
    <section class=\"panel\">
      <div class=\"bar\">
        <span><strong>Source</strong> {source}</span>
        <span><strong>Retrieved</strong> {retrieved}</span>
        <span><strong>SHA-256</strong> {content_hash}</span>
        <span><strong>Original</strong> <a href=\"{original_url}\" target=\"_blank\" rel=\"noopener noreferrer\">Open source</a></span>
      </div>
      <pre>{content}</pre>
    </section>
    <div class=\"note\">This is a captured web-context snapshot, not a replacement for the authoritative source record and not an adjudication of any claim.</div>
  </main>
</body>
</html>"""
    return HTMLResponse(
        content=document,
        headers={"Cache-Control": "public, max-age=86400"},
    )
