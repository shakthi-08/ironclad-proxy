# Ironclad Proxy SOC Dashboard

This is a Next.js 14 + Tailwind CSS telemetry panel for the Python security
daemon. It polls `/api/telemetry` every five seconds and sends the manual
kill-switch to `/api/lockdown`.

## Connecting the Python daemon



Set `IRONCLAD_PROXY_API_URL` in the dashboard environment to the base URL of a
small daemon adapter that exposes:

- `GET /telemetry` returning `TelemetrySnapshot` JSON
- `POST /lockdown` setting the daemon's `is_frozen` state

Telemetry requests must include an `x-signature` HMAC-SHA256 header generated
with the same `IRONCLAD_HMAC_SECRET` used by the daemon. Missing signatures
return `401`; invalid signatures return `403`.

The UI intentionally returns a simulation snapshot when the variable is absent,
so local frontend development is safe and visibly marked as `simulation`.

```text
cd dashboard
npm install
$env:IRONCLAD_PROXY_API_URL = "http://127.0.0.1:8080"
npm run dev
```

<!-- build trigger -->


