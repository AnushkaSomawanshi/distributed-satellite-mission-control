# FA-2 Phase 1 + 2 — Unit 3 algorithms running on the satellites

> All five FA-2 phases are now complete. Start with **[FA2_GUIDE.md](FA2_GUIDE.md)** (full syllabus
> coverage, results and demo script 15–30); this file keeps the Phase 1–2 details.

**Status:** implemented and verified (unit tests + live 5-satellite run).
Gate 1 ("Causality Lens on real messages") and Gate 2 ("Arena shows measured runs") are met.

## Design rule

Every Unit 3 algorithm runs **inside the five satellite processes** and exchanges real messages over
their P2P ports. Mission Control only:

- forwards commands (start an election, inject a fault, run an experiment),
- collects the events satellites report and computes metrics from them,
- acts as the time server for Cristian's algorithm.

It never decides a leader, grants a lock or adjusts a clock. Earlier Mission-Control-only versions
(`election_manager.py`, `experiment_lab.py`, `beacon_service.py`, `registry.run_ring_election`, the
`/api/mutex/*` endpoints and their pages) were removed.

## Where the code is

| Path | What it does |
|---|---|
| `satellites/dsync/clocks.py` | Physical clock (offset + drift), Lamport clock, vector clock (implements the FA-1 `ILamportClock` / `IVectorClock` interfaces) |
| `satellites/dsync/transport.py` | Stamped satellite-to-satellite messages, peer directory, partition + crash enforcement |
| `satellites/dsync/events.py` | Per-satellite event log, buffered and shipped in batches (survives Mission Control outages) |
| `satellites/dsync/beacon.py` | Beacon protocol: discovery, failure detection (SUSPECTED 3 s, DEAD 5 s), clock-offset estimates |
| `satellites/dsync/election.py` | Bully + Ring, one implementation, leader + term, automatic re-election |
| `satellites/dsync/clocksync.py` | Cristian (best of 3 samples) and Berkeley (leader as time daemon) |
| `satellites/dsync/mutex.py` | Centralised, Ricart–Agrawala, Token Ring, Lodha–Kshemkalyani |
| `satellites/dsync/node.py` | Wires it together; `/dsync/*` HTTP API on each satellite |
| `backend/fa2/` | Mission Control: event collector, `/api/fa2/*` API, measured metrics |
| `frontend/src/pages/{CausalityLens,LeaderElection,ClockSync,AlgorithmArena}Page.jsx` | The four FA-2 pages (sidebar: *Distributed algorithms*) |
| `tests/test_fa2_algorithms.py` | Core guarantee of every algorithm on 5 in-process satellites |
| `scripts/fa2_phase2_probe.py` | Same checks against the live system (exit code 0 = gate passed) |

## Messages and events

Every algorithm message is stamped with the sender's Lamport clock, vector clock and physical clock.
Both ends record an event (`SEND` / `RECV`); decisions are `LOCAL` events (`LEADER_ELECTED`,
`CS_ENTER`, `CLOCK_ADJUSTED`, `PEER_DEAD`, …). Satellites publish event batches to the RabbitMQ
fanout exchange `dsync.events` (HTTP fallback `/api/fa2/events` when no broker is reachable).

Beacons are control-plane traffic and do **not** tick logical clocks, otherwise the causality view
would be flooded; liveness changes they cause are stamped local events.

## Faults, enforced by the satellites

| Fault | Effect on the satellite |
|---|---|
| `CLOCK_DRIFT` | Jumps the satellite's clock and/or sets a drift rate (ppm) |
| `PARTITION` | The satellite refuses to send to, or accept from, satellites outside its group |
| `CRASH` (also the existing `STOP` fault) | The satellite goes silent: no heartbeats, telemetry, gossip, beacons or algorithm messages |
| `RECOVER` (also `RESTART`) | Back to normal; with Bully it holds an election, as in the textbook algorithm |

The existing `/api/network/partition`, `/api/faults/inject` and `/api/faults/clear` now push these to
the satellites too. A crash is simulated (the process keeps its control port so Mission Control can
recover it); stopping a container is the real thing and is detected the same way.

## Measured results (live run, 5 satellites, local processes, RabbitMQ)

| Algorithm | Result |
|---|---|
| Bully from SAT-01 | 24 messages, all agree in ~130 ms (worst case: lowest satellite starts) |
| Ring from SAT-01 | 10 messages (5 ELECTION + 5 COORDINATOR), ~130–190 ms |
| Leader crash | Beacons declare it dead after ~4–7 s; survivors agree on a new leader ~0.15 s later |
| Berkeley | Clock spread 1600 ms → 2 ms |
| Cristian | Max skew from true time 61 ms → 1.8 ms |
| Ricart–Agrawala | 8.0 messages per entry = 2(N−1); 0 fairness inversions |
| Lodha–Kshemkalyani | 7.2–7.6 messages per entry; 0 fairness inversions |
| Centralised | 2.4 messages per entry (leader's own requests are local) |
| Token Ring | 0.7–1.8 messages per entry (depends on load) |
| All four mutex | never two satellites in the critical section |

Numbers vary run to run; the Arena always shows the latest measured values.

## Honest notes for the viva

- **Ground truth.** All processes share one host clock, so satellites can report their true skew.
  The algorithms never read it; it is only used to check the result.
- **Lodha–Kshemkalyani.** On exit a satellite sends FLUSH to *every* concurrent requester in its
  local request queue (not only the next one). This keeps the entry rule simple and provably safe;
  messages stay between N−1 and 2(N−1).
- **Bully priority** is (health rounded down to tens, ID), not the ID alone.
- **Token Ring** circulates only while an Arena run is active; the token parks otherwise.
- **Phase 3–5 update:** snapshots, task redistribution, deadlock detection, the ledger and the status board
  now also run on the satellites; Mission Control's old in-memory clock, snapshot, mutex, partition and
  security services were removed.

## Verify it yourself

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest                         # all tests, including tests/test_fa2_algorithms.py

docker compose up --build -d
python scripts/fa2_phase2_probe.py       # live gate checks; expect "All FA-2 Phase 1 + 2 gate checks passed."
```

Then open `http://localhost:3000` → sidebar **Distributed algorithms**.

## Demo script (continues Demo 1–14)

| Demo | Page | Steps | What to point out |
|---|---|---|---|
| 15 Causality | Causality Lens | Inject CLOCK_DRIFT −800 ms on SAT-02 → Send 10 cross-links → switch *Order by* between Physical, Lamport, Vector | Red arrows = receives before their send on physical clocks; none under Lamport/vector |
| 16 Concurrency | Causality Lens | Click two events on different satellites with no message path between them | "concurrent" from the vector clocks |
| 17 Clock sync | Clock Sync | Drift 3 satellites → Run Berkeley → Run Cristian | Spread collapses with Berkeley; Cristian also pulls clocks to true time |
| 18 Election | Leader Election | Start Bully from SAT-01, then Ring | 24 vs 10 messages; every card shows the same leader + term |
| 19 Failover | Leader Election | Crash the leader & measure failover | Peer cards turn SUSPECTED → DEAD; survivors elect without Mission Control |
| 20 Mutex arena | Algorithm Arena | Run all four | Messages/entry vs theory; zero overlaps; R–A and L–K have zero fairness inversions |
| 21 Partition | Fault Controls / API | Partition {01,02,03} vs {04,05} | Cross-partition sends fail at the satellites; HEAL restores them |
