import { requestLockdown } from "@/lib/telemetry";

export const runtime = "nodejs";

export async function POST() {
  try {
    await requestLockdown();
    return Response.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Lockdown unavailable";
    return Response.json({ error: message }, { status: 503 });
  }
}
