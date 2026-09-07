import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const storeDir = path.join(process.cwd(), "data");
const storeFile = path.join(storeDir, "field-map-flags.json");

async function readFlags() {
  try {
    const raw = await fs.readFile(storeFile, "utf8");
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export async function GET() {
  const flags = await readFlags();
  return NextResponse.json({ flags });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    if (!Array.isArray(body?.flags)) {
      return NextResponse.json({ error: "flags must be an array" }, { status: 400 });
    }

    const sanitized = body.flags.slice(0, 500).filter((flag: any) =>
      flag &&
      typeof flag.id === "string" &&
      Number.isFinite(Number(flag.lat)) &&
      Number.isFinite(Number(flag.lon)) &&
      typeof flag.type === "string",
    );

    await fs.mkdir(storeDir, { recursive: true });
    await fs.writeFile(storeFile, JSON.stringify(sanitized, null, 2), "utf8");
    return NextResponse.json({ ok: true, count: sanitized.length });
  } catch {
    return NextResponse.json({ error: "Could not persist field map flags" }, { status: 500 });
  }
}
