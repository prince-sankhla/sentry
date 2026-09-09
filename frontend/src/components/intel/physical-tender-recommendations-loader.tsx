"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { PhysicalTenderRecommendations, type TenderRecommendation } from "./physical-tender-recommendations";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

type Payload = {
  field_ready: TenderRecommendation[];
  pothole: TenderRecommendation[];
};

export function PhysicalTenderRecommendationsLoader() {
  const [data, setData] = useState<Payload | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`${BACKEND_URL}/api/investigations/tender-recommendations?pothole_limit=200&field_limit=200`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Recommendation endpoint returned ${response.status}`);
        return (await response.json()) as Payload;
      })
      .then((payload) => alive && setData(payload))
      .catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, []);

  if (failed) {
    return (
      <div className="mt-8 rounded-2xl border border-border bg-surface p-4 text-sm text-muted">
        Physical/pothole recommendations are temporarily unavailable. The generic investigation queue remains available below.
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mt-8 flex items-center gap-2 rounded-2xl border border-border bg-surface p-4 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-accent" /> Loading live physical-verification and pothole tender recommendations…
      </div>
    );
  }

  return <PhysicalTenderRecommendations fieldReady={data.field_ready} pothole={data.pothole} />;
}
