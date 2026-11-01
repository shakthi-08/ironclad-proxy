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

export const simulation: TelemetrySnapshot = {
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

export function readTelemetry(): TelemetrySnapshot {
  return {
    ...simulation,
    events: simulation.events.map((event) => ({ ...event })),
  };
}
