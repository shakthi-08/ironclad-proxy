import { readTelemetry } from "@/lib/telemetry";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toHex(bytes: Uint8Array) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function signaturesMatch(expected: string, provided: string) {
  if (!/^[\da-fA-F]+$/.test(provided)) {
    return false;
  }

  if (expected.length !== provided.length) {
    return false;
  }

  let difference = 0;
  for (let index = 0; index < expected.length; index += 1) {
    difference |= expected.charCodeAt(index) ^ provided.charCodeAt(index);
  }
  return difference === 0;
}

export async function GET(request: Request) {
  const secret = (
    globalThis as typeof globalThis & {
      process?: { env?: Record<string, string | undefined> };
    }
  ).process?.env?.IRONCLAD_HMAC_SECRET;
  if (!secret) {
    return Response.json({ error: "Telemetry signing is not configured" }, { status: 500 });
  }

  const providedSignature = request.headers.get("x-signature");
  if (!providedSignature) {
    return Response.json({ error: "Missing x-signature header" }, { status: 401 });
  }

  try {
    const telemetry = await readTelemetry();
    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const signature = await crypto.subtle.sign(
      "HMAC",
      key,
      new TextEncoder().encode(JSON.stringify(telemetry)),
    );
    const expectedSignature = toHex(new Uint8Array(signature));
    const normalizedSignature = providedSignature.replace(/^sha256=/i, "");

    if (!signaturesMatch(expectedSignature, normalizedSignature)) {
      return Response.json({ error: "Invalid telemetry signature" }, { status: 403 });
    }

    return Response.json(telemetry);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Telemetry unavailable";
    return Response.json({ error: message }, { status: 502 });
  }
}
