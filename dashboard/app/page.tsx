"use client";

// React is supplied by the Next.js runtime; keep the page buildable when its
// ambient package types are unavailable in the editor's current workspace.
// @ts-ignore
import { useState } from "react";
import { readTelemetry, type TelemetrySnapshot, type TransactionEvent } from "@/lib/telemetry";

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elementName: string]: any;
    }
  }
}

const initial: TelemetrySnapshot = readTelemetry();

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function statusStyle(status: TransactionEvent["status"]) {
  if (status === "accepted") return "bg-signal/10 text-signal";
  if (status === "blocked") return "bg-danger/10 text-danger";
  return "bg-warning/10 text-warning";
}

export default function Dashboard() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(initial);
  const [locking, setLocking] = useState(false);

  function lockdown() {
    if (telemetry.isFrozen) return;
    setLocking(true);
    setTelemetry((current: TelemetrySnapshot) => ({
      ...current,
      isFrozen: true,
      events: [
        {
          id: `evt-lockdown-${Date.now()}`,
          timestamp: new Date().toISOString(),
          status: "tripped",
          detail: "Emergency lockdown · local simulation",
          amountUsd: 0,
        },
        ...current.events,
      ],
    }));
    setLocking(false);
  }

  const percentage = Math.min(
    100,
    (telemetry.rollingOutflowUsd / telemetry.velocityLimitUsd) * 100,
  );

  return (
    <main className="min-h-screen bg-ink px-5 py-6 text-slate-100 sm:px-10 lg:px-16">
      <header className="mx-auto flex max-w-7xl flex-col justify-between gap-5 border-b border-line pb-6 sm:flex-row sm:items-center">
        <div>
          <div className="mb-2 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.3em] text-slate-500">
            <span className="h-2 w-2 rounded-full bg-signal pulse-ring" />
            Ironclad Proxy · Security Operations Center
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Hot wallet telemetry
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Pre-execution enforcement · {telemetry.windowSeconds}s rolling
            window
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`rounded-full border px-3 py-2 text-xs font-bold uppercase tracking-wider ${telemetry.isFrozen ? "border-danger/40 bg-danger/10 text-danger" : "border-signal/30 bg-signal/10 text-signal"}`}
          >
            {telemetry.isFrozen
              ? "Circuit breaker tripped"
              : "Protection active"}
          </span>
          <button
            type="button"
            disabled={locking || telemetry.isFrozen}
            onClick={() => void lockdown()}
            className="rounded-lg border border-danger/50 bg-danger px-4 py-3 text-xs font-black tracking-wider text-white transition hover:bg-danger/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {locking ? "LOCKING..." : "EMERGENCY LOCKDOWN"}
          </button>
        </div>
      </header>

      <section className="mx-auto mt-8 grid max-w-7xl gap-5 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-2xl border border-line bg-panel p-6 shadow-glow">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                Rolling velocity
              </p>
              <p className="mt-3 text-4xl font-semibold">
                {money(telemetry.rollingOutflowUsd)}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                of {money(telemetry.velocityLimitUsd)} maximum outflow
              </p>
            </div>
            <span className="rounded-md border border-line px-2 py-1 text-xs text-slate-400">
              SIMULATED · LOCAL
            </span>
          </div>
          <div className="mt-10">
            <div className="mb-3 flex justify-between text-xs font-semibold text-slate-400">
              <span>$0</span>
              <span>{percentage.toFixed(1)}% utilized</span>
              <span>$1M</span>
            </div>
            <div className="h-5 overflow-hidden rounded-full bg-ink">
              <div
                className={`h-full rounded-full transition-all duration-700 ${percentage > 80 ? "bg-danger" : percentage > 60 ? "bg-warning" : "bg-signal"}`}
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="mt-5 grid grid-cols-3 gap-3 text-center text-xs">
              <div className="rounded-lg border border-line bg-ink/50 p-3">
                <strong className="block text-slate-100">{money(0)}</strong>
                <span className="text-slate-500">window start</span>
              </div>
              <div className="rounded-lg border border-line bg-ink/50 p-3">
                <strong className="block text-signal">
                  {money(telemetry.rollingOutflowUsd)}
                </strong>
                <span className="text-slate-500">current outflow</span>
              </div>
              <div className="rounded-lg border border-line bg-ink/50 p-3">
                <strong className="block text-slate-100">
                  {money(
                    Math.max(
                      0,
                      telemetry.velocityLimitUsd - telemetry.rollingOutflowUsd,
                    ),
                  )}
                </strong>
                <span className="text-slate-500">remaining headroom</span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-line bg-panel p-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
            Enforcement state
          </p>
          <div className="mt-7 flex items-center gap-4">
            <div
              className={`h-16 w-16 rounded-full border-4 ${telemetry.isFrozen ? "border-danger bg-danger/10" : "border-signal bg-signal/10"} flex items-center justify-center`}
            >
              <span
                className={`h-4 w-4 rounded-full ${telemetry.isFrozen ? "bg-danger" : "bg-signal"}`}
              />
            </div>
            <div>
              <p className="text-xl font-semibold">
                {telemetry.isFrozen ? "GLOBAL FREEZE" : "ARMED"}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {telemetry.isFrozen
                  ? "All inbound transactions isolated"
                  : "Pre-execution gate is accepting traffic"}
              </p>
            </div>
          </div>
          <div className="mt-8 border-t border-line pt-5 text-xs text-slate-500">
            <div className="flex justify-between">
              <span>Telemetry source</span>
              <span className="font-semibold text-slate-300">
                {telemetry.source}
              </span>
            </div>
            <div className="mt-3 flex justify-between">
              <span>Method policy</span>
              <span className="font-mono text-slate-300">0xa9059cbb</span>
            </div>
            <div className="mt-3 flex justify-between">
              <span>Blocked type</span>
              <span className="font-mono text-danger">0x04</span>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-5 max-w-7xl rounded-2xl border border-line bg-panel p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
              Transaction stream
            </p>
            <h2 className="mt-2 text-xl font-semibold">Live security events</h2>
          </div>
          <span className="text-xs text-slate-500">
            {telemetry.events.length} events · source: {telemetry.source}
          </span>
        </div>
        <div className="space-y-2">
          {telemetry.events.length === 0 && (
            <p className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-slate-500">
              No simulated events yet.
            </p>
          )}
          {telemetry.events.map((event: TransactionEvent) => (
            <div
              key={event.id}
              className="grid gap-3 rounded-lg border border-line bg-ink/40 p-4 text-sm sm:grid-cols-[150px_110px_1fr_130px] sm:items-center"
            >
              <span className="font-mono text-xs text-slate-500">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span
                className={`w-fit rounded px-2 py-1 text-[10px] font-black uppercase tracking-wider ${statusStyle(event.status)}`}
              >
                {event.status}
              </span>
              <span className="text-slate-300">{event.detail}</span>
              <span className="text-right font-mono text-slate-400">
                {money(event.amountUsd)}
              </span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
