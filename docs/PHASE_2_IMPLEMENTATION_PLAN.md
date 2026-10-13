# Phase 2 — Correctness, Recovery, and Observable Distributed Behavior

**Status:** Proposed implementation plan; not evidence that implementation or runtime tests have passed.  
**Branch:** `phase-2-implementation-plan`  
**Depends on:** Phase 1 source audit and runtime-baseline automation.  
**Project direction:** **OrbitGuard — Self-Healing Distributed Satellite Mission Control**.

## 1. Phase 2 objective

Turn the existing multi-service application into a trustworthy, demonstrable distributed-systems project before adding more visual polish. The core demonstration should show a real node/coordinator failure, failure detection, leader election, safe task recovery, and measurable recovery outcomes across SAT-01 through SAT-05.

Phase 2 prioritizes correctness and evidence over adding more screens. Existing pages should remain usable, but must not present fallback values, inferred state, or illustrative graphics as live observations.

### Phase 2 exit outcome

A reviewer can start the stack, observe five registered nodes, submit a uniquely identified task, interrupt a node in a controlled test, observe the election and recovery event trail, and inspect measured outcomes. If a behavior is not implemented or instrumented, the UI and report say so explicitly.

## 2. Ground rules

1. **No invented telemetry or metrics.** Missing, invalid, stale, simulated, and measured values must be distinguishable.
2. **One source of truth for node and leader state.** Frontend labels must reflect backend/API/event state rather than independent assumptions.
3. **Failure detection is not failure proof.** A missed heartbeat first makes a node suspect; policy and elapsed timeout determine when it is considered unavailable.
4. **Election is not task correctness.** A new leader does not, by itself, make in-flight work safe to retry.
5. **At-least-once delivery may cause retries.** Use stable task IDs, idempotent completion, ownership/fencing checks, and duplicate-attempt accounting. Do not claim exactly-once execution unless the system can actually guarantee and test it.
6. **Simulation and real fault injection are separate.** Label API-driven simulations as simulations. Container termination tests must be isolated to a disposable test environment.
7. **Measure rather than guess.** Every latency, recovery time, and count in a demo report must come from recorded timestamps or counters.
8. **Small reviewable pull requests.** Work on feature branches, add tests with behavior changes, and merge in dependency order.
9. **Keep the existing stack first.** Docker Compose is the Phase 2 baseline. Kubernetes or extra infrastructure is not a prerequisite.
10. **Never report a check as passing without captured evidence.**

## 3. Priority order and work packages

### P0 — Confirm and capture the runtime baseline

**Why first:** The source audit and CI probe are not substitutes for an observed run. Implementation changes need a reproducible starting point.

**Tasks**
- Run the Phase 1 GitHub Actions workflow and inspect its actual status and logs.
- Run `docker compose config`, `docker compose up --build -d`, `docker compose ps`, and `python scripts/phase1_baseline.py` in the target environment.
- Record service startup, health, registration, API, and WebSocket results. Preserve the command output and relevant logs.
- Fix baseline blockers before layering in protocol changes. Separate environmental failures (Docker unavailable, image pull failure) from application defects.
- Add a dated baseline record to the audit document only after the run is observed.

**Deliverables**
- Verified baseline report with environment, commit SHA, command results, failures, and links to logs.
- A short blocker list ordered by severity.

**Acceptance**
- Workflow result is inspected, not inferred from workflow-file existence.
- All five node IDs are either observed in the registry or the exact missing-node failure is documented.
- Any failed baseline check has a reproducible error and an owner/work item.

### P1 — Define canonical data contracts and remove fabricated telemetry

**Why:** Incorrect inputs or synthetic history undermine every dashboard, metric, and experiment.

**Backend work**
- Define a telemetry schema: satellite ID, observation timestamp, required measurement fields, units, schema/version marker if needed, and optional fields.
- Validate types, ranges, timestamp format, and node identity at ingestion.
- Choose and document behavior for invalid or incomplete messages: reject, or persist as explicitly incomplete with field-level quality errors. Never replace missing measurements with plausible readings.
- Keep observation time and server receive time distinct where possible.
- Add structured warnings/errors for invalid telemetry; avoid logging secrets or excessively noisy per-message errors.
- Verify that health scores are calculated only from valid inputs and identify the formula/version used.

**Frontend work**
- Remove seeded fallback telemetry history from `App.jsx`.
- Add explicit states: loading, no observations yet, stale data, incomplete observation, disconnected, and error.
- Validate incoming WebSocket payloads before adding chart points.
- Do not convert missing health score to 100 or missing node status to HEALTHY.
- Drive the “WebSocket live” indicator from the actual connection lifecycle.

**Tests**
- Missing required field; wrong type; out-of-range value; malformed timestamp; unknown satellite; valid message.
- Empty initial history; malformed WebSocket event; socket disconnect/reconnect; stale observation.
- Assert that no synthetic point appears and invalid payloads cannot silently become healthy telemetry.

**Acceptance**
- No default measurement is persisted or rendered as a received observation.
- Each chart point can be traced to a validated source observation and timestamp.
- Unknown is never rendered as healthy.

### P2 — Standardize satellite lifecycle and heartbeat failure detection

**Why:** Election and recovery need consistent membership information.

**Tasks**
- Inventory all heartbeat handlers, registry updates, status constants, TTLs, and status calculations across backend and satellite services.
- Define a single documented state machine, for example: `STARTING → HEALTHY → SUSPECTED → OFFLINE`, with an explicit recovery transition when valid heartbeats resume. Preserve existing names only if the codebase’s semantics justify them.
- Define the difference between stale heartbeat, suspected node, unavailable node, and administratively stopped node.
- Centralize timeout/threshold configuration and expose effective settings in diagnostics.
- Make status transitions timestamped and observable; avoid contradictory status values from separate components.
- Handle clock assumptions explicitly. Use monotonic time for elapsed local timeout measurement where applicable; use wall-clock timestamps for event records.
- Ensure restart/re-registration behavior does not leave stale membership entries.

**Tests**
- Heartbeat arrives on time.
- Heartbeat just before, at, and just after the configured threshold.
- Several missed heartbeats.
- Recovery heartbeat after suspicion/offline.
- Node restart and re-registration.
- Delayed/out-of-order heartbeat and duplicate registration.

**Acceptance**
- Backend API, election eligibility, registry page, telemetry page, and incident trail agree on node state.
- Threshold tests are deterministic and do not rely on arbitrary sleeps where a controllable clock can be used.
- Detection delay is recorded from configured threshold and observed timestamps, not described as instantaneous.

### P3 — Establish one authoritative coordinator election path

**Why:** Multiple election implementations or stale coordinator state can create conflicting leadership.

**Discovery before coding**
- Trace the ring-election API, satellite-side election logic, leader storage, heartbeat/registry membership, and frontend consumers.
- Document which service initiates election, the eligible-node rule, ring ordering, tie-breaking, timeout policy, and how the result is persisted and broadcast.
- Check behavior when the initiator is offline, one or more ring members are missing, messages are delayed, or two elections overlap.

**Implementation**
- Choose one authoritative election result path and make other code call or consume it instead of maintaining competing leader calculations.
- Make election runs identifiable with an election/run ID and record initiator, eligible membership view, messages/steps where available, result, start/end timestamps, and outcome.
- Validate initiator and eligible members against current membership.
- Make concurrent/repeated requests safe and define what happens if the elected node becomes unavailable during the election.
- Store the current leader and term/epoch (or another monotonic leadership generation) in an authoritative location suitable for the current architecture.
- Broadcast/publish the result to observers and update UI from the result/event rather than optimistic local state.

**Tests**
- Normal ring election.
- Initiator unavailable.
- Highest-ID candidate unavailable.
- One intermediate ring member unavailable.
- Repeated request and concurrent election request.
- Coordinator failure during election.
- Deterministic election outcome for the same membership view.

**Acceptance**
- There is one auditable current leader and a trace for each election.
- Tests prove no unavailable node is selected under the defined membership policy.
- The UI labels election in progress, completed, and failed separately; it does not claim success before the backend confirms it.

### P4 — Make task ownership and recovery safe under coordinator/node failure

**Why:** A leader change must not silently lose work or execute a task twice.

**Discovery before coding**
- Trace task creation, storage, assignment, status transitions, execution location, reassignment endpoint, retries, and completion writes.
- Identify whether task records are persisted in PostgreSQL, memory, or both, and what happens if the process or database restarts.
- Identify current task identifiers and whether retries reuse the same ID.

**Implementation**
- Define a task lifecycle and legal transitions, such as pending, assigned, running, retryable, completed, failed, and cancelled. Adapt names to the existing model and keep one canonical definition.
- Assign every submitted task a stable unique ID and retain it through reassignment/retry.
- Record owner, attempt number, lease/claim expiry if used, timestamps, result, and failure reason.
- Use an atomic claim/transition in the authoritative store so two nodes cannot both acquire the same current task claim.
- Use a lease or claim expiry for abandoned work, with a fencing token/monotonic generation when stale workers could complete after reassignment.
- Make completion idempotent: duplicate completion for the same task ID and attempt should not apply side effects twice.
- Reject or ignore stale completions from a previous owner/term. Record rejected stale writes for debugging.
- Define retry policy, max attempts, backoff, terminal failure behavior, and manual replay/retry semantics.
- Add a reconciliation path after coordinator change or worker timeout; recovery must use persisted task state rather than UI guesses.
- Ensure fault injection and cancellation clean up safely, and keep destructive container tests isolated to a disposable Compose project.

**Tests**
- Normal task completes once.
- Worker fails before starting.
- Worker fails while running.
- Old worker reports completion after reassignment.
- Same task is submitted twice with the same idempotency key.
- Two workers attempt to claim the same task concurrently.
- Coordinator restarts while a task is pending/running.
- Database restart and task-state reload.
- Max retries reached.
- Recovery after leader election.

**Acceptance**
- For each test task ID, report attempts, final state, and duplicate side-effect count.
- A simulated failure and a real process/container termination are reported separately.
- No exactly-once claim is made unless the tests and design substantiate it; target idempotent effects and auditable retry behavior.

### P5 — Instrument the distributed behavior

**Why:** The project needs evidence of distributed-systems behavior, not just a visually compelling dashboard.

**Tasks**
- Define correlation IDs for experiments, election runs, task IDs, fault events, and relevant messages.
- Add structured event records for node state changes, election start/result, task assignment/claim/reassignment/completion, injected faults, and recovery decisions.
- Capture timestamps with clear semantics: event created, sent, received, persisted, and completed where available.
- Instrument measured durations:
  - failure detection = observed suspicion/unavailable transition minus fault start time;
  - election duration = election completion minus election start;
  - task recovery = task reassignment/reclaim or final completion minus fault start, with exact definition documented;
  - task success/failure and attempts per task;
  - duplicate completion/side-effect attempts;
  - WebSocket connection state and event delivery gaps where measurable.
- Track metric units, aggregation window, source, and sample count. Show “not measured” when instrumentation is unavailable.
- Keep simulated timestamps/results marked as simulation data.

**Tests**
- Unit tests for metric calculations from known timestamp sequences.
- Correlation ID remains consistent across related events.
- Missing timestamps produce “not measured,” not zero.
- Repeated experiment runs do not accidentally combine unrelated metrics.

**Acceptance**
- A demo report can be generated from actual recorded events.
- Every displayed number has a documented source and formula.
- No performance target is declared achieved until repeated runs produce measured evidence.

### P6 — Harden Compose configuration and persistence

**Tasks**
- Move credentials and environment-specific values to environment variables; add a safe `.env.example` with placeholders only and document local setup.
- Avoid committing actual secrets. Explain that Compose environment variables are a local-development convenience, not a production secret manager.
- Review host port exposure; publish only ports needed for local development.
- Add a named PostgreSQL volume if durable local data is intended, and document reset behavior. Do not use destructive `down -v` on a developer's data.
- Add meaningful health checks for backend and satellite services if reliable readiness endpoints exist.
- Make satellite startup wait for backend readiness where Compose supports it; still implement retry/backoff in the satellite because dependency ordering alone does not ensure ongoing availability.
- Define restart policies and graceful shutdown behavior where appropriate.
- Ensure CI uses a disposable project name, isolated data, and cleanup even on failure.

**Tests**
- Compose config validation.
- Clean first startup.
- Backend/satellite restart.
- Database container recreation with named volume.
- Explicit disposable-volume reset test.
- Confirm secrets do not appear in repository diff or application logs.

**Acceptance**
- Fresh-clone local setup is documented.
- Persistence behavior is demonstrated and intentional.
- CI cleanup cannot remove a developer's unrelated Compose volumes.
- Health checks indicate readiness meaningfully, not merely that a process exists.

### P7 — Complete route/API/UI smoke coverage and data provenance

**Tasks**
- Visit all registered routes from the Phase 1 inventory.
- Build a route-to-API/WebSocket/source matrix, including empty, loading, stale, error, and disconnected states.
- Fix silent fetch-error handling so failures are visible in a useful non-alarming banner/toast and diagnosable in console logs.
- Test WebSocket connect, reconnect, unmount cleanup, and stale-connection behavior.
- Verify each dashboard visual is tagged internally/documented as live, derived, illustrative, or unavailable.
- Keep Earth imagery/orbit arcs clearly illustrative unless a real coordinate/orbit model is implemented and fed by real data.
- Add browser automation only after the local stack can be started deterministically in CI; prioritize critical flows over screenshot-only assertions.
- Test at common desktop and narrow viewport sizes; check keyboard focus and accessible labels for controls.

**Critical UI flows**
1. Overview shows API-backed node/service counts and honest no-data state.
2. Registry status and last heartbeat agree with backend.
3. Telemetry charts remain empty until real valid samples arrive.
4. Election action reports pending/result/error based on backend response.
5. Fault simulation clearly indicates simulated vs real fault scope.
6. Task reassignment shows task ID, owner/attempt, and resulting status.
7. Incidents/replay distinguish persisted observed events from generated examples.
8. Each route loads without uncaught console errors or failed required requests.

**Acceptance**
- Every route is checked in browser automation or has a recorded, explicit reason it remains manual.
- The live connection indicator follows actual connection state.
- No UI page converts missing data into a healthy or successful state.

### P8 — Professional UI pass after correctness fixes

**Why last:** Styling must expose correct behavior instead of masking missing or invalid data.

**Design direction**
- Preserve the premium aerospace operations visual language and compact layout already established.
- Make real node health, leader/term, active experiment, task recovery, and service connectivity the highest-signal elements.
- Use consistent status colors and labels, with text/icon labels so color is not the only signal.
- Provide contextual empty/error/loading states and last-updated timestamps.
- Keep topology, geographic map, and orbit illustration distinct; do not imply actual orbital position without coordinates and a defined calculation.
- Make event timelines, election steps, task attempts, and metric provenance inspectable.
- Keep charts focused on measured trends, with units, time range, sample count, and missing-data behavior.
- Ensure smaller viewports remain usable without hiding critical state.

**Acceptance**
- Each major screen answers: what is happening, what evidence supports it, and what action is safe next?
- Visual changes do not alter protocol behavior or fabricate values.
- Screenshot review is paired with functional checks.

## 4. Pull request sequence

Keep each PR narrow enough to review and revert independently.

| Order | Proposed PR | Scope | Required evidence |
|---|---|---|---|
| 1 | Phase 2 baseline evidence | Inspect Actions and record first real baseline results; fix baseline blockers only | CI result, Compose output, probe output, logs |
| 2 | Telemetry contract and validation | Schema, validation, ingestion errors, unit tests | Valid/invalid payload test report |
| 3 | Remove synthetic frontend telemetry | Empty/loading/stale states; truthful WebSocket indicator | Frontend tests and browser screenshots/logs |
| 4 | Canonical node lifecycle | State machine, heartbeat thresholds, transition tests | Boundary/recovery test results |
| 5 | Election source-of-truth | Single election path, term/epoch, audit events | Election scenario matrix |
| 6 | Durable task lifecycle | Stable IDs, atomic claims, idempotent completion, fencing/retry policy | Concurrency and duplicate-attempt tests |
| 7 | Real controlled recovery experiment | Disposable integration harness for node termination and recovery | Timestamped experiment output; cleanup evidence |
| 8 | Metrics and experiment report | Correlation IDs, measured durations, run summaries | Report generated from captured events |
| 9 | Compose hardening | Config, health/readiness, volume, ports, startup retry | Clean-start/restart/persistence test output |
| 10 | Route/browser smoke suite | Critical flows, route checks, WebSocket lifecycle | Automated report and console/network error list |
| 11 | Data-backed UI polish | Overview, telemetry, election, tasks, incident/observability pages | Functional checks plus visual review |

Do not start a downstream PR if its required upstream contract is still undecided. If baseline reveals a blocking defect, insert a small repair PR before proceeding.

## 5. Test strategy

Use layers so defects are found cheaply before expensive end-to-end tests.

1. **Unit tests:** telemetry validation, health calculation, state transitions, election ordering/eligibility, task transition rules, idempotency decisions, metric formulas.
2. **Component/service integration tests:** API plus registry/database, RabbitMQ telemetry ingestion, WebSocket publication, concurrent task claims.
3. **Compose integration tests:** five-node registration, restart behavior, persistence, election/recovery against disposable services.
4. **Fault experiments:** terminate one selected satellite container in an isolated project; observe detection, election, task recovery, and cleanup. Test coordinator and worker failures separately.
5. **Browser smoke tests:** critical routes and workflows, empty/error/reconnect states, console/network errors, responsive layout.
6. **Repeatability:** run the same scenario multiple times with unique experiment IDs; preserve logs and raw event records. Report sample count and observed range rather than only a best run.

### Minimum experiment record

- Experiment ID and commit SHA.
- Start/end timestamps and clock source.
- Fault type and target service.
- Pre-fault leader, eligible membership, and task ID (if applicable).
- Configured heartbeat/election/retry timeouts.
- Ordered event timeline.
- Resulting leader and leadership generation.
- Task attempts, final status, and duplicate side-effect count.
- Detection, election, and recovery durations with formula.
- Container/service logs and test output.
- Cleanup confirmation.
- Known limitations and whether the run was simulated or a real process/container fault.

## 6. Definition of done for Phase 2

Phase 2 is done only when all of the following have evidence:

- [ ] Five satellite nodes register reliably on a clean Compose startup.
- [ ] Telemetry schema validation rejects or explicitly marks incomplete data; no fabricated observations appear.
- [ ] Node state transitions and heartbeat thresholds are documented and tested.
- [ ] One authoritative coordinator result is recorded for every completed election.
- [ ] A controlled real node/container failure is detected and produces an auditable election outcome.
- [ ] A task interrupted during execution is recovered according to documented retry/ownership policy.
- [ ] Duplicate submission/completion and stale-worker completion tests demonstrate safe idempotent behavior.
- [ ] Persistence and restart behavior are explicitly tested.
- [ ] Detection, election, and recovery metrics are calculated from captured timestamps; uninstrumented metrics are marked not measured.
- [ ] Critical frontend routes and WebSocket lifecycle are smoke-tested.
- [ ] UI does not present missing data, simulated events, or illustrative orbit graphics as live facts.
- [ ] Setup, experiment procedure, expected evidence, and known limitations are documented.
- [ ] No check is marked passed without an actual test result.

## 7. Explicit non-goals for Phase 2

- Do not add Kubernetes solely to make the project look more distributed.
- Do not add more dashboard screens before the underlying metrics and state are trustworthy.
- Do not claim real orbital propagation, satellite geolocation, exactly-once execution, or production-grade consensus unless those capabilities are implemented and tested.
- Do not run real failure-injection tests against a developer's everyday Compose stack or persistent data.
- Do not optimize performance before measuring a correct baseline.

## 8. Immediate next action

1. Inspect the actual GitHub Actions run for the merged Phase 1 baseline workflow.
2. Run the documented baseline on Docker Desktop and capture output.
3. Fix any startup or probe blockers.
4. Start the first correctness PR with telemetry contract/validation, unless baseline reveals a more fundamental startup blocker.
5. Update this plan and the audit with actual results as they become available; keep proposed work marked pending until tested.
