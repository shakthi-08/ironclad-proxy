import { NextResponse } from "next/server";
import { readTelemetry } from "@/lib/telemetry";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json(await readTelemetry());
  } catch (error) {
    const message = error instanceof Error ? error.message : "Telemetry unavailable";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
