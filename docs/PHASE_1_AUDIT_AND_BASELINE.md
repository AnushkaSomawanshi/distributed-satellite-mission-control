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


## 10. Frontend route inventory (source-level)

The following routes are explicitly registered in `frontend/src/App.jsx`. This verifies route registration only; it does not imply that each route has passed a browser or API integration test.

| Route | Page component | Initial audit focus |
|---|---|---|
| `/` | `MissionOverview` | Distinguish real registry/service data from illustrative orbital artwork; verify service-health source and empty states. |
| `/tasks` | `MissionTasksPage` | Task identity, ownership, status transitions, retries and reassignment evidence. |
| `/clocks` | `ClockSyncPage` | Clock assumptions, offset calculation and source of displayed values. |
| `/ring-election` | `RingElectionPage` | API response, initiator validation, offline-node behavior, authoritative leader and event trace. |
| `/mutex` | `MutexManagerPage` | Concurrent request behavior, critical-section safety and timeout/release handling. |
| `/snapshots` | `GlobalSnapshotPage` | Snapshot completeness, message/state consistency and provenance. |
| `/failure-intelligence` | `FailureIntelligencePage` | Evidence source, detection timestamps and distinction between observation and inference. |
| `/incidents` | `IncidentConsolePage` | Event ordering, incident lifecycle and persistence. |
| `/experiments` | `ExperimentLabPage` | Repeatability, scenario configuration and measured outcomes. |
| `/partition` | `PartitionReconciliationPage` | Conflict policy, convergence and reconciliation audit trail. |
| `/topology` | `ConstellationMap` | Topology data source and separation of network links from geographic/orbital positions. |
| `/observatory` | `CommunicationObservatory` | Message/event provenance, correlation IDs and accurate protocol/latency labels. |
| `/replay` | `CommunicationReplay` | Whether replay uses captured events or generated examples; deterministic ordering. |
| `/concepts` | `DistributedConcepts` | Each concept linked to a working demonstration or clearly labeled explanation. |
| `/faults` | `FaultSimulatorPage` | Fault injection scope, cleanup, node impact and observable recovery. |
| `/registry` | `SatelliteRegistryPage` | Canonical status vocabulary, last heartbeat and missing-data behavior. |
| `/telemetry` | `LiveTelemetryPage` | Real observations only, no synthetic history, truthful WebSocket status indicator. |
| `/multimedia` | `MultimediaPage` | WebRTC/P2P state and clear unavailable/unsupported states. |
| `/middleware` | `MiddlewarePage` | Which middleware/protocol path is actually exercised by each control. |
| `/demo-center` | `SystemHealthDemo` | Whether the demo runs the system or only presents a scripted visualization. |
| `/runtime-observability` | `RuntimeObservabilityPage` | Actual runtime metrics vs placeholders and their collection interval. |

### Cross-cutting frontend observations

- `App.jsx` polls `/api/satellites`, `/api/health`, `/api/observatory/stats`, and `/api/faults` on a three-second interval. The baseline should verify response status and payload shape; the current catch blocks suppress fetch errors, so a failure may be hard to diagnose from the UI alone.
- The WebSocket URL is derived from the current page origin and reconnects after a fixed delay on close. The baseline should verify reconnect behavior and cleanup after navigation/unmount.
- The `TELEMETRY_UPDATED` handler converts incoming values to numbers and uses a health-score fallback. Missing/non-numeric fields should be validated before adding chart points.
- `LiveTelemetryPage` displays a fixed “WEBSOCKET LIVE” label in the inspected source. This label should be driven by the actual `wsConnected` state (or another explicit connection status), not a static visual indicator.
- `LiveTelemetryPage` derives an SAT-02 offline banner from the status string and defaults absent SAT-02 status to `HEALTHY`. The audit must check that this does not present a healthy state when status is unknown.
- The `RingElectionPage` calls `POST /api/election/ring?initiator_id=...`. This route and its response semantics must be matched against the backend implementation and the behavior of the independent satellite services.

## 11. Compose configuration observations (source-level)

- PostgreSQL and RabbitMQ declare health checks. The backend uses `depends_on` with healthy conditions for those two dependencies.
- Satellite services use `depends_on: mission-control` without a health condition; this orders startup but does not prove the API is ready to accept registration/heartbeats.
- The inspected Compose file defines static database and RabbitMQ connection credentials inline. Replace deployment credentials with environment inputs; provide a safe example configuration without real secrets.
- The inspected Compose file does not show a PostgreSQL named volume. Verify whether database data is expected to survive container recreation; add persistence only in line with the intended local-development behavior.
- Backend and satellite services do not show explicit Compose health checks in the inspected file. Decide which readiness/liveness checks are meaningful and implement them in a later hardening task.
- Ports for PostgreSQL, RabbitMQ management, backend, satellite gRPC/P2P ports, and frontend are published to the host. Review whether all are needed for local development and avoid broad exposure in shared deployments.

## 12. Evidence status and Phase 1 completion gate

This audit now contains a source-level route inventory and configuration review. It remains important to distinguish these completed repository actions from runtime verification:

| Activity | Evidence status |
|---|---|
| Audit document committed to GitHub | Complete; merged in PR #6 |
| Frontend route list extracted from `App.jsx` | Complete at source level |
| Initial telemetry fallback paths identified | Complete at source level |
| Compose dependency, credential, and persistence risks recorded | Complete at source level |
| GitHub Actions workflow runs found for the Phase 1 merge commit | No associated runs were returned |
| Docker Compose startup and container health | Pending execution in a Docker environment |
| API and WebSocket integration checks | Pending execution |
| Failure/election/task recovery experiments | Pending execution |
| Browser smoke test of every route | Pending execution |
| Actual recovery/latency/resource measurements | Pending execution |

**Phase 1 is not marked runtime-complete until the pending checks are executed and their observed outputs are recorded.** A GitHub source audit cannot truthfully certify the user's Docker Desktop state or browser behavior. The next audit update should attach command output, test logs, and measured timestamps instead of converting the plan into assumed pass results.
