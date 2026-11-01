import * as telemetry from "@/lib/telemetry";

export const runtime = "nodejs";

export async function POST() {
  try {
    const requestLockdown = (
      telemetry as typeof telemetry & {
        requestLockdown?: () => Promise<void>;
      }
    ).requestLockdown;

    if (!requestLockdown) {
      throw new Error("Lockdown unavailable");
    }

    await requestLockdown();
    return Response.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Lockdown unavailable";
    return Response.json({ error: message }, { status: 503 });
  }
}
