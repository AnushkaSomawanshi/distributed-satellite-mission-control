# Phase 2 Implementation Status and Verification Guide

**Current status:** Phase 2 implementation is in progress. This document records the first merged-ready correctness slice, not completion of all Phase 2 acceptance criteria.

## Implemented in the telemetry-integrity change

- Added a Pydantic telemetry observation contract with required measurements and bounds.
- Made heartbeat measurements required rather than silently filling omitted fields with nominal-looking defaults.
- Changed RabbitMQ telemetry ingestion to reject invalid/incomplete observations and log a validation warning rather than calculating health from fabricated readings.
- Removed frontend code that manufactured five historical chart points from the current registry snapshot.
- Frontend history now accepts telemetry events only when required measurements are present and numeric; health score is not defaulted to 100.
- The telemetry screen now reflects the actual WebSocket connection state and labels an absent SAT-02 registry record as UNKNOWN rather than HEALTHY.
- Added unit tests for valid data, missing measurements, and invalid ranges, plus a GitHub Actions workflow for those tests.

## Not yet completed

The following remain open and must not be considered passed just because the code above exists:

- Execute and inspect the Phase 1 Compose/runtime baseline.
- Verify the telemetry handler against actual RabbitMQ messages in the running stack.
- Define and test the canonical node-state machine and configurable heartbeat thresholds.
- Unify the election implementation and authoritative leader/term source.
- Implement and test durable task ownership, idempotent completion, stale-worker fencing, and retry policy.
- Run a real, isolated satellite/container failure experiment and prove task recovery.
- Instrument and report actual detection, election, and recovery durations.
- Verify PostgreSQL persistence and restart behavior.
- Automate browser smoke tests across all routes and responsive states.
- Finish Compose secret/configuration/health-check hardening and data-backed UI polish.

## A. Pull the code and start the stack

Open PowerShell in the project folder in VS Code:

```powershell
git switch main
git pull origin main
docker compose config
docker compose up --build -d
docker compose ps
```

Wait until containers have started. If a service exits or remains unhealthy, collect:

```powershell
docker compose ps -a
docker compose logs --tail=150 mission-control
docker compose logs --tail=100 satellite-01 satellite-02 satellite-03 satellite-04 satellite-05
docker compose logs --tail=100 frontend
```

Do not run `docker compose down -v` against a development stack unless you intentionally want to delete its named volumes/data. The Phase 1 disposable CI workflow can tear down its own isolated environment; local developer data is different.

## B. Run the baseline probe

Install the WebSocket client dependency into the Python environment used by the terminal, then run:

```powershell
python -m pip install websockets
python scripts/phase1_baseline.py
```

The probe checks the health/API endpoints, expected node registration, observatory stats, task API, ring-election endpoint, coordinator-failure simulation endpoint, frontend HTTP response, and WebSocket handshake. It does **not** kill a real satellite container or prove durable task recovery.

Save the complete terminal output. A nonzero exit code means at least one probe failed; use the reported endpoint and Compose logs to diagnose it.

## C. Run telemetry contract unit tests

These tests only need Pydantic and the repository source. In a Python environment where Pydantic can be installed:

```powershell
python -m pip install "pydantic>=1.10,<3"
python -m unittest discover -s tests -p "test_telemetry_schema.py" -v
```

Expected test names:
- `test_valid_observation_is_accepted`
- `test_missing_measurement_is_rejected`
- `test_out_of_range_measurement_is_rejected`
- `test_heartbeat_does_not_fill_missing_measurements`
- `test_invalid_cpu_range_is_rejected`

The expected outcome is five passing tests. This is a test expectation, not a claim that they have already run on your machine. GitHub Actions should also run the contract test workflow for the relevant push/PR.

## D. Verify in the UI

Open `http://localhost:3000` in your browser.

1. **Mission overview:** check whether satellite/service counts populate. If not, inspect the API and frontend logs rather than assuming the UI is live.
2. **Telemetry page:** open `http://localhost:3000/telemetry`.
3. Before the first valid WebSocket telemetry event, the page should show “No telemetry observations received yet”; charts should not show fabricated historical points.
4. Check the connection pill. It should say “WEBSOCKET CONNECTED” only while the socket is open, and “WEBSOCKET DISCONNECTED” when it is not connected.
5. If SAT-02 is absent from the registry response, the page should say its status is unknown, not healthy.
6. After valid samples arrive, charts should begin to populate. Refresh the page and confirm the chart starts empty again until new live samples arrive; history is intentionally not reconstructed from current registry values.
7. Use browser Developer Tools → Console and Network. Record failed API requests, WebSocket handshake failures, and uncaught exceptions.

## E. Verify API responses

In PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/satellites
Invoke-RestMethod http://localhost:8000/api/observatory/stats
Invoke-RestMethod http://localhost:8000/api/tasks
```

Confirm that the satellite list includes SAT-01 through SAT-05. If it does not, save the response and inspect the corresponding satellite container logs.

To check that required heartbeat fields are not silently defaulted, send an intentionally incomplete request only to a disposable local development stack:

```powershell
$body = @{
  satellite_id = "SAT-TEST"
  battery = 80
  cpu_usage = 20
  memory_usage = 30
  signal_strength = 90
} | ConvertTo-Json

try {
  Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/satellites/heartbeat -ContentType "application/json" -Body $body
} catch {
  Write-Host "Expected validation rejection:" $_.Exception.Message
}
```

The request intentionally omits `temperature`; FastAPI should return a validation error (normally HTTP 422). Do not use a real or shared deployment for this negative test.

## F. Verify WebSocket telemetry

The simplest first check is the telemetry page plus the baseline script's WebSocket handshake. A successful handshake alone does not prove telemetry events are arriving. For an actual event test:

- Keep the telemetry page open.
- Confirm satellite logs show successful heartbeat/telemetry publishing.
- Confirm charts begin to update only after valid samples.
- Stop/restart the frontend page connection using browser DevTools or reload the page and confirm the connection indicator reflects the connection lifecycle.
- Check backend logs for “Rejected invalid telemetry payload” if malformed RabbitMQ data is intentionally tested in an isolated environment.

## G. Record results

For every check, write down:
- commit SHA and date/time;
- command or browser route;
- observed result (PASS/FAIL/BLOCKED);
- relevant logs or screenshot;
- exact failure message if failed.

Do not mark real coordinator failure, task recovery, duplicate-execution safety, persistence, or all-route browser coverage as passing until those separate experiments have actually been performed.
