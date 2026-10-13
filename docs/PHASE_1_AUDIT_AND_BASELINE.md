# Phase 1 — Repository Audit and Baseline

**Status:** Initial static audit recorded; runtime baseline is still pending.  
**Branch:** `phase-1-audit-baseline`  
**Audit approach:** Repository source/configuration inspection. No claim is made that Docker Compose, browser flows, or failure experiments were executed by this audit.

## 1. Purpose

Establish a trustworthy baseline before implementation changes. Identify the architecture, current UI surfaces, correctness risks, baseline experiments, and acceptance criteria for subsequent phases. Preserve the existing application and make changes through reviewable pull requests.

## 2. Architecture inventory

The repository currently documents a containerized system with:

- React frontend.
- FastAPI Mission Control backend.
- Five satellite node services (SAT-01 through SAT-05).
- PostgreSQL.
- RabbitMQ.
- REST and WebSocket communication, with additional gRPC/P2P/WebRTC-related components described by the README.

The Compose configuration includes PostgreSQL and RabbitMQ health checks and makes the backend dependent on those services being healthy. Satellite services depend on the Mission Control service. This configuration has not been runtime-tested as part of this audit.

Primary files inspected:

- `README.md`
- `docker-compose.yml`
- `backend/main.py`
- `satellites/satellite_node.py`
- `frontend/src/App.jsx`
- `frontend/src/pages/MissionOverview.jsx`

## 3. Initial findings

### P1 — Missing telemetry fields can be replaced with plausible defaults

**Location:** `backend/main.py`, RabbitMQ telemetry handling.

The inspected telemetry path supplies fallback values for missing fields (including battery, temperature, CPU, memory, and signal strength) before calculating health and updating the registry.

**Risk:** An incomplete message may be displayed as if it contained real measurements, masking schema or transport defects.

**Required follow-up:** Define the telemetry schema; validate required fields and types; distinguish missing/invalid measurements from actual values; log or emit a data-quality event; do not silently substitute operational measurements.

**Acceptance:** A message missing a required measurement is rejected or explicitly marked incomplete. No fabricated value is persisted or represented as a received measurement.

### P1 — Frontend initializes telemetry history with fallback readings

**Location:** `frontend/src/App.jsx`, satellite data/history initialization.

The inspected code seeds a short history when history contains fewer than three points and uses fallback readings for battery, temperature, CPU, and health score.

**Risk:** Initial charts can imply historical observations that were not received from a satellite or backend.

**Required follow-up:** Trace REST and WebSocket data paths; initialize history as empty; add points only from validated observations; represent no-data/loading states explicitly.

**Acceptance:** With no telemetry events, charts show an empty/loading state rather than invented measurements. Received points remain attributable to their source and timestamp.

### P1 — Satellite state vocabulary needs a canonical contract

**Locations:** Backend registry/heartbeat handling and frontend status presentation; full cross-file verification remains open.

The repository refers to multiple states such as suspected, disconnected, and offline. Their semantics and transitions must be consistent.

**Risk:** Different pages or services can disagree about whether a node is alive, suspected, or unavailable.

**Required follow-up:** Inventory every state constant, transition, timeout, and UI mapping. Document one canonical state contract and transition table before changing behavior.

**Acceptance:** Backend and UI use the same documented meanings; tests cover threshold boundaries and recovery after a heartbeat resumes.

### P1 — Election and recovery paths require a single end-to-end trace

**Locations:** Election/coordination modules and related pages; exact duplicate implementations and behavior still require cross-file verification.

**Risk:** Multiple paths may calculate or display leadership differently, or election may not guarantee safe recovery of in-flight tasks.

**Required follow-up:** Locate each election implementation and caller; document election eligibility, ordering, timeout assumptions, coordinator source of truth, and how the result is broadcast. Separately trace task ownership, retry, idempotency, and conflict handling.

**Acceptance:** A controlled coordinator failure produces one authoritative leader decision and a recorded outcome. Task recovery tests explicitly detect duplicate execution; leader election alone is not treated as an exactly-once guarantee.

### P2 — Live, calculated, and illustrative visuals must be clearly distinguished

**Location:** `frontend/src/pages/MissionOverview.jsx` and telemetry/chart components.

The overview uses external Earth imagery and illustrative orbital arcs, and includes a geographic map panel. These visual elements do not by themselves establish live orbital positions or computed ground tracks.

**Risk:** Viewers may mistake decorative or geographic context for measured satellite position and trajectory.

**Required follow-up:** Inventory every dashboard metric and visual with its data source and classify it as live, derived, illustrative, or unavailable. Keep illustrative overlays labeled; only plot satellite positions/tracks when grounded in actual coordinates and a defined model.

**Acceptance:** Every live metric has a traceable API/event source; illustrative content is labeled; unavailable values are not invented.

### P2 — Configuration and persistence need a deployment-readiness review

**Location:** `docker-compose.yml`.

The inspected configuration contains a static PostgreSQL password. PostgreSQL persistence and backend/satellite health-check behavior need explicit verification.

**Risk:** Credentials may be unsuitable for shared deployment; data persistence and restart behavior may be misunderstood.

**Required follow-up:** Move credentials to environment/configuration inputs (with an example env file that contains no real secrets), review port exposure, verify volumes and restart behavior, and add appropriate service health checks where justified.

**Acceptance:** No production credential is committed; local startup instructions are documented; persistence and restart expectations are tested.

## 4. Screen inventory to complete

The README and frontend routing describe a multi-page application. Each route must be inspected and recorded with its API/event source and test status. Areas to include:

- Mission overview and constellation map.
- Satellite registry/detail and telemetry.
- Fault simulation and incident/failure intelligence.
- Communication observatory and replay.
- Distributed concepts and topology.
- Ring election, distributed mutex, global snapshot, and clock synchronization.
- Task scheduling/reallocation.
- Experiments, runtime observability, and partition reconciliation.

This is an inventory scope, not a claim that each page has been fully validated. The full route-to-component-to-endpoint mapping remains open.

## 5. Baseline execution plan

Run and record these checks on the development environment before behavior changes:

1. **Compose startup:** `docker compose config`, then `docker compose up --build -d`; record service health and logs.
2. **API readiness:** check the backend health/readiness endpoint if present; otherwise record the actual existing endpoint and response.
3. **Node registration:** verify SAT-01 through SAT-05 appear in the registry.
4. **Telemetry integrity:** observe an actual telemetry message and compare payload, registry record, API response, and chart point.
5. **Heartbeat timeout:** delay/stop one node and record transition timestamps and configured thresholds.
6. **WebSocket lifecycle:** confirm events arrive; interrupt/restart the backend and record reconnect behavior.
7. **Coordinator failure:** identify current leader, stop it, record election events and resulting leader.
8. **Task recovery:** submit a uniquely identified task, interrupt its owner/coordinator at a controlled point, and record final status and duplicate-execution count.
9. **Persistence/restart:** restart relevant containers and check which records survive.
10. **UI smoke test:** visit every route; check console/network errors, empty-data states, and responsive layouts.

**Execution status:** These are pending baseline checks. This repository audit did not execute them, so no pass/fail result or performance number is asserted here.

## 6. Metrics to capture (actual observations only)

For each controlled run, record run ID, scenario, node(s) affected, configured timeouts, event timestamps, and outcome. Capture:

- Failure detection time.
- Election duration.
- Recovery time.
- Tasks submitted/completed/failed.
- Duplicate task execution count.
- Message latency where send/receive timestamps are available.
- Queue depth where exposed by RabbitMQ instrumentation.
- CPU and memory use when measured by the runtime.

If a metric is not currently instrumented, mark it **not measured**; do not estimate or fill it with placeholder values.

## 7. Prioritized follow-up backlog

1. Remove synthetic/default telemetry from backend and frontend paths.
2. Define canonical satellite status semantics and test transitions.
3. Trace election and task recovery end to end; resolve inconsistent sources of truth.
4. Add deterministic tests for telemetry validation, heartbeat transitions, election, and task idempotency.
5. Complete route/API/event inventory and baseline UI smoke tests.
6. Add measurement instrumentation for failure detection, election, recovery, and task outcomes.
7. Review configuration, persistence, health checks, and deployment secrets.
8. After correctness is established, extend the dashboard with data-backed mission metrics and clearly labeled orbital/ground-track visualization.

## 8. Exit criteria for Phase 1

Phase 1 is complete when:

- [ ] Every route is mapped to its component and data source.
- [ ] The initial findings above are verified against all relevant call sites.
- [ ] Docker Compose startup and API readiness results are recorded.
- [ ] All five nodes are verified in the registry.
- [ ] Telemetry, heartbeat, WebSocket, election, task-recovery, and persistence baseline results are recorded.
- [ ] Metrics that cannot yet be measured are explicitly listed.
- [ ] Follow-up work is ordered by correctness and dependency.
- [ ] No runtime test is reported as passing without an observed result.

## 9. Environment and limitations

This document records source-level findings and a repeatable plan. The audit did not execute containers, browser automation, failure injection, or performance experiments. Runtime behavior may differ from what static inspection suggests; all pending items must be verified in the target environment.
