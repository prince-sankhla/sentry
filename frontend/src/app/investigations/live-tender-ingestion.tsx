"use client";

import { ArrowRight, DownloadCloud, Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LiveTenderIngestion() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function ingest() {
    const value = url.trim();
    if (!value) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/live-ingestion/cppp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: value }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Could not fetch the CPPP tender.");
      router.push(`/tenders/${payload.tender_pk}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live ingestion failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel mt-5 p-6">
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-accent/20 bg-accent/10 p-2 text-accent">
          <DownloadCloud className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="text-xs font-medium uppercase tracking-[0.14em] text-accent">Live Indian ingestion</div>
          <h2 className="mt-1 text-base font-semibold text-text">Investigate a live CPPP tender</h2>
          <p className="mt-1 text-sm text-muted">Paste the official eProcurement detail URL. SENTRY fetches the current page, preserves provenance, extracts documents, normalizes the tender, and opens its investigation surface.</p>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
        <Input
          fieldSize="lg"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://eprocure.gov.in/eprocure/app?...FrontEndTender..."
          className="flex-1"
          disabled={loading}
        />
        <Button
          variant="primary"
          size="lg"
          type="button"
          className="px-6"
          onClick={ingest}
          disabled={loading || !url.trim()}
          trailing={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
        >
          {loading ? "Fetching…" : "Fetch & investigate"}
        </Button>
      </div>
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </div>
  );
}
