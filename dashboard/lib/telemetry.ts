export type TransactionStatus = "accepted" | "blocked" | "tripped";

export type TransactionEvent = {
  id: string;
  timestamp: string;
  status: TransactionStatus;
  detail: string;
  amountUsd: number;
};

export type TelemetrySnapshot = {
  isFrozen: boolean;
  rollingOutflowUsd: number;
  velocityLimitUsd: number;
  windowSeconds: number;
  events: TransactionEvent[];
  source: "python-daemon" | "simulation";
};

const simulation: TelemetrySnapshot = {
  isFrozen: false,
  rollingOutflowUsd: 100000,
  velocityLimitUsd: 1000000,
  windowSeconds: 60,
  source: "simulation",
  events: [
    {
      id: "evt-001",
      timestamp: new Date().toISOString(),
      status: "accepted",
      detail: "ERC-20 transfer · 0xa9059cbb",
      amountUsd: 100000
    }
  ]
};

export async function readTelemetry(): Promise<TelemetrySnapshot> {
  const baseUrl = process.env.IRONCLAD_PROXY_API_URL;
  if (!baseUrl) return simulation;

  const response = await fetch(`${baseUrl}/telemetry`, {
    cache: "no-store",
    signal: AbortSignal.timeout(2500)
  });
  if (!response.ok) throw new Error(`Telemetry backend returned ${response.status}`);
  return (await response.json()) as TelemetrySnapshot;
}

export async function requestLockdown(): Promise<void> {
  const baseUrl = process.env.IRONCLAD_PROXY_API_URL;
  if (!baseUrl) {
    throw new Error("IRONCLAD_PROXY_API_URL is not configured");
  }
  const response = await fetch(`${baseUrl}/lockdown`, {
    method: "POST",
    cache: "no-store",
    signal: AbortSignal.timeout(2500)
  });
  if (!response.ok) throw new Error(`Lockdown backend returned ${response.status}`);
}
