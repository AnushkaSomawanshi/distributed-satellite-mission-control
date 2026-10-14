# FA-2 — Complete Guide (Units 3 and 4)

**Status:** all five FA-2 phases implemented and verified: 52 automated tests, plus two live probes that
run every algorithm against 5 satellite processes, RabbitMQ, a primary and a standby Mission Control and
the Nginx gateway (`scripts/fa2_phase2_probe.py`, `scripts/fa2_full_probe.py`).

**Design rule:** every distributed algorithm runs **inside the satellite processes** and exchanges real
messages over their P2P links. Mission Control starts experiments, collects events, mirrors state and
checks results; it never decides a leader, grants a lock, adjusts a clock or moves a task.

## 1. Syllabus coverage

### Unit 3 — Synchronization

| Topic | Implementation | Code | Page |
|---|---|---|---|
| Clock synchronization | Per-satellite drifting clock; **Cristian** (best of 3, Mission Control as time server) and **Berkeley** (leader as daemon) | `satellites/dsync/clocks.py`, `clocksync.py` | Clock Sync |
| Logical clocks / Lamport | Every message stamped; `L = max(L, received) + 1` | `clocks.py`, `transport.py` | Causality Lens |
| Vector clocks | 5-entry vector on every message; happened-before / concurrent tests | `clocks.py`, `transport.py` | Causality Lens |
| Global state | **Chandy–Lamport** markers over FIFO channels; channel recording; task-conservation check | `snapshot.py`, `backend/fa2/phase3.py` | Global Snapshot |
| Election algorithms | **Bully** and **Ring**, one implementation with leader + term; priority = (health, ID); auto re-election | `election.py` | Leader Election, Arena |
| Mutual exclusion | **Centralised**, **Ricart–Agrawala**, **Token Ring** on the ground-station downlink | `mutex.py` | Algorithm Arena |
| Beacon protocol | Beacons every 2 s: discovery, failure detection (3 s suspect, 5 s dead), clock offsets | `beacon.py` | Leader Election |
| Self-study: Lodha–Kshemkalyani | Fair mutex with local request queues and FLUSH | `mutex.py` | Algorithm Arena |
| Self-study: Knapp's classification | **Chandy–Misra–Haas** edge-chasing detection + youngest-victim resolution; the four classes explained | `deadlock.py` | Deadlock Detection |

### Unit 4 — Emerging distributed paradigms

| Topic | Implementation | Code | Page |
|---|---|---|---|
| Distributed object-based systems | **Pyro5**: each satellite exports a stateful `PayloadController` registered in a name server | `satellites/dsync/remote_objects.py`, `backend/fa2/objects.py` | Cloud & Data Lab |
| Distributed web-based systems | **Nginx gateway**: static frontend, API + WebSocket proxy, 1 s micro-cache, rate limiting, warm-standby failover | `docker/gateway/nginx.conf`, `backend/fa2/role.py` | Cloud & Data Lab |
| Distributed file system | **OrbitFS**: NameNode (Mission Control) + DataNodes (satellites), 3-way pipeline replication, SHA-256, self-healing | `satellites/dsync/datanode.py`, `backend/fa2/orbitfs.py` | OrbitFS |
| Serverless architectures | Process-per-instance runtime: cold/warm starts, scale to zero, RabbitMQ-triggered functions | `backend/fa2/serverless.py`, `functions.py` | Cloud & Data Lab |
| Case study: Apache Hadoop | MapReduce over OrbitFS: data-local map tasks on satellites, combiner, shuffle, reduce, re-execution | `datanode.py`, `backend/fa2/mapreduce.py` | Cloud & Data Lab |
| Case study: Kubernetes | Satellites as a StatefulSet, MC primary + standby, gateway, probes (validated against k8s 1.29) | `k8s/` | — |
| Case studies: AWS, Cloudflare, Megaport | Mapping onto the architecture | `docs/CASE_STUDIES.md` | Cloud & Data Lab |
| Self-study: blockchain / ledger | Hash-chained command ledger, Ed25519 proof of authority, majority quorum, tamper detection + repair | `satellites/dsync/ledger.py`, `backend/fa2/phase5.py` | CAP |
| Self-study: distributed DB trade-offs | **CAP** under one partition: ledger is CP (minority refuses), status board is AP (vector-clock conflicts) | `ledger.py`, `statusboard.py` | CAP |

### USPs

| USP | Where |
|---|---|
| **Ground Blackout Mode** — the constellation keeps coordinating with no ground segment and reports afterwards in causal order | Ground Blackout page, `node.py`, `phase3.py` |
| **Causality Lens** — live space-time diagram under physical / Lamport / vector ordering | Causality Lens page |
| **Algorithm Arena** — measured comparison of 2 election and 4 mutex algorithms | Algorithm Arena page |
| **Tamper-evident command ledger** | CAP page |
| **Split-brain-safe task ownership** — version fencing + majority quorum | Mission Tasks page, `tasks.py` |

## 2. How the pieces fit

```
 Browser ──▶ Nginx gateway :8080 ──▶ Mission Control (primary)   ┐ same RabbitMQ fanout streams,
                  │  cache, rate limit └▶ Mission Control (standby)┘ standby passive until primary dies
                  ▼
 Satellites (5 processes) ── heartbeats / Cristian time ──▶ gateway
   │  P2P (FIFO, Lamport+vector stamped): beacons, elections, mutex, snapshots, deadlock probes,
   │                                      task handoff, ledger votes, status board, OrbitFS pipeline
   ├─ events + telemetry ──▶ RabbitMQ (dsync.events, telemetry.exchange) ──▶ Mission Control
   └─ Pyro5 PayloadController ──▶ name server in Mission Control
```

## 3. Run and verify

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest                                   # 52 passed

docker compose up --build -d                       # dashboard: http://localhost:8080 (gateway)
python scripts/fa2_phase2_probe.py --base-url http://localhost:8080
python scripts/fa2_full_probe.py   --base-url http://localhost:8080
```

Kubernetes: see `k8s/README.md`.

## 4. Measured results (live run, local processes behind Nginx, RabbitMQ)

| What | Result |
|---|---|
| Bully / Ring election from SAT-01 | 24 / 10 messages, all agree in ~0.13–0.2 s |
| Leader crash → new leader | ~4–5.5 s (dominated by the 5 s beacon detector) |
| Berkeley / Cristian | spread 1600 ms → 2–41 ms / max skew ~65 ms → ~1.5 ms |
| Mutex messages per entry | Ricart–Agrawala 8.0 = 2(N−1); Lodha–Kshemkalyani 7.2–7.6; Centralised 2.4; Token Ring 0.7–1.8 |
| Mutex safety / fairness | never two in the critical section; R–A and L–K 0 fairness inversions |
| Chandy–Lamport | 20 markers (5 × 4); every snapshot conserves all 5 tasks; tasks caught in transit |
| Deadlock (3-cycle) | detected ~1.4 s after blocking (1 s probe delay), 6–8 probe messages, one victim; chain: no false alarm |
| Ground blackout (30–40 s, one crash) | survivors declare it dead, move its tasks, run Berkeley alone; 16–23 events delivered after contact returns |
| OrbitFS | crash a DataNode → under-replicated chunks back to 3 copies within ~4 s; extras trimmed on return |
| MapReduce | 4–8 chunks, all map tasks data-local, ~0.3 s |
| Serverless | cold start ~60–110 ms (new process), warm reuse, scale to zero after 20 s |
| Pyro5 call | 2–8 ms, state kept between calls |
| Gateway | cache MISS → HIT within 1 s; failover to standby ~6 s after the primary dies |
| CAP | majority side commits with 3 signatures, minority refused with 2; board conflict seen on all 5 after healing |

## 5. Demo script (continues Demo 1–14)

| # | Page | Steps | Point out |
|---|---|---|---|
| 15 | Causality Lens | Drift SAT-02 −800 ms → send cross-links → switch ordering | Red arrows only under physical time |
| 16 | Causality Lens | Click two unrelated events | "concurrent" from vector clocks |
| 17 | Clock Sync | Drift 3 satellites → Berkeley → Cristian | Spread collapses; Cristian aligns to true time |
| 18 | Leader Election | Bully, then Ring | 24 vs 10 messages, same leader + term everywhere |
| 19 | Leader Election | Crash the leader & measure failover | SUSPECTED → DEAD → new leader without Mission Control |
| 20 | Algorithm Arena | Run all four mutex algorithms | Messages/entry vs theory, zero overlaps, fairness |
| 21 | Mission Tasks | Crash a task owner | Leader moves its task (version + 1); returning satellite is fenced |
| 22 | Global Snapshot | Start handoff traffic → take snapshots | Tasks in channels; invariant holds |
| 23 | Deadlock Detection | Cycle, then chain | Probe returns → victim; chain → probes dropped |
| 24 | Ground Blackout | Cut the link 45 s, crash SAT-05 at 8 s | Autonomous mode; causal timeline afterwards |
| 25 | OrbitFS | Upload an image → crash a holder | Re-replication; image_stats function fired |
| 26 | Cloud & Data Lab | Archive telemetry → run MapReduce | Data-local map tasks, reducers on satellites |
| 27 | Cloud & Data Lab | Invoke incident_report twice | Cold then warm start, same PID |
| 28 | Cloud & Data Lab | Pyro: point → capture ×2 → status | Remote object keeps state (vs stateless gRPC) |
| 29 | Cloud & Data Lab | Probe gateway; `docker compose stop mission-control` | Cache HIT; standby takes over |
| 30 | CAP | Partition → ledger on both sides → board writes on both sides → heal → resolve | CP refuses on minority; AP conflict detected and resolved |

## 6. Honest notes for the viva

- **Ground truth for clocks:** all processes share one host clock, so satellites report their true skew;
  the algorithms never read it.
- **Crash = simulated** (satellite goes silent but keeps its control port so it can be recovered);
  stopping a container is the real thing and is detected the same way.
- **Lodha–Kshemkalyani:** FLUSH goes to every concurrent requester in the local queue (not only the next),
  which keeps the entry rule simple and safe; message count stays between N−1 and 2(N−1).
- **Beacons** do not tick logical clocks (control-plane traffic).
- **Split brain:** both partition sides elect a leader; only a leader that reaches 3 of 5 satellites may move
  tasks or commit ledger blocks. Found and fixed during testing — see `test_partition_does_not_cause_split_brain_task_ownership`.
- **Ground blackout** in the UI is simulated by Mission Control refusing satellite traffic; `docker compose
  stop mission-control mission-control-standby` produces the real thing.
- **Standby replica** keeps its own in-memory event store (from the same RabbitMQ fanout); NameNode metadata
  is shared through a volume.
- **OrbitFS chunk data** lives in satellite memory; a restarted satellite comes back empty and the NameNode
  re-replicates.
