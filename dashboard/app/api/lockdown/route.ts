import { NextResponse } from "next/server";
import { requestLockdown } from "@/lib/telemetry";

export const runtime = "nodejs";

export async function POST() {
  try {
    await requestLockdown();
    return NextResponse.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Lockdown unavailable";
    return NextResponse.json({ error: message }, { status: 503 });
  }
}
