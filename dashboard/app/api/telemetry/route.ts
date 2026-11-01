import { readTelemetry } from "@/lib/telemetry";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    return Response.json(await readTelemetry());
  } catch (error) {
    const message = error instanceof Error ? error.message : "Telemetry unavailable";
    return Response.json({ error: message }, { status: 502 });
  }
}
