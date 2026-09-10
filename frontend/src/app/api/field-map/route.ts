import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const storeDir = path.join(process.cwd(), "data");
const storeFile = path.join(storeDir, "field-map-flags.json");

type Flag = {
  id: string;
  lat: number;
  lon: number;
  type: string;
  tender_id?: string | null;
  [key: string]: unknown;
};

async function readFlags(): Promise<Flag[]> {
  try {
    const raw = await fs.readFile(storeFile, "utf8");
    const data = JSON.parse(raw);
    return Array.isArray(data) ? (data as Flag[]) : [];
  } catch {
    return [];
  }
}

export async function GET(request: Request) {
  const tenderId = new URL(request.url).searchParams.get("tender_id")?.trim() || "";
  const flags = await readFlags();
  const scoped = tenderId ? flags.filter((flag) => flag.tender_id === tenderId) : [];
  return NextResponse.json({ flags: scoped });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const tenderId = typeof body?.tender_id === "string" ? body.tender_id.trim() : "";
    if (!tenderId || !Array.isArray(body?.flags)) {
      return NextResponse.json({ error: "tender_id and flags are required" }, { status: 400 });
    }

    const sanitized = body.flags
      .slice(0, 500)
      .filter((flag: any) =>
        flag &&
        typeof flag.id === "string" &&
        Number.isFinite(Number(flag.lat)) &&
        Number.isFinite(Number(flag.lon)) &&
        typeof flag.type === "string",
      )
      .map((flag: any) => ({ ...flag, tender_id: tenderId }));

    const existing = await readFlags();
    const retained = existing.filter((flag) => flag.tender_id !== tenderId);
    const merged = [...retained, ...sanitized].slice(0, 5000);

    await fs.mkdir(storeDir, { recursive: true });
    await fs.writeFile(storeFile, JSON.stringify(merged, null, 2), "utf8");
    return NextResponse.json({ ok: true, count: sanitized.length });
  } catch {
    return NextResponse.json({ error: "Could not persist field map flags" }, { status: 500 });
  }
}
