# FA-2 EXTENSION ARCHITECTURE

This project (FA-1) has been designed specifically so that **FA-2 Distributed Systems** topics can be cleanly added without modifying core satellite communication loops.

---

## Extension Interface Stubs (`backend/fa2_extensions/interfaces.py`)

1. **Lamport Clocks (`ILamportClock`)**:
   - Maintains scalar logical clock $L$.
   - Event rule: $L_{local} = \max(L_{local}, L_{received}) + 1$.

2. **Vector Clocks (`IVectorClock`)**:
   - Vector timestamp $V[i]$ tracking causal history across $N=5$ satellites.

3. **Leader Election (`ILeaderElection`)**:
   - Bully / Ring election algorithms when the elected leader node fails.

4. **Distributed Mutual Exclusion (`IDistributedMutex`)**:
   - Ricart-Agrawala algorithm for shared orbital resource access (e.g. ground station downlink channel lock).

5. **Global State Snapshot (`IGlobalStateSnapshot`)**:
   - Chandy-Lamport distributed snapshot algorithm to record consistent global state across all 5 satellites.

6. **Autonomous Task Redistribution (`ITaskScheduler`)**:
   - Redistributes failed satellite orbital tasks to remaining healthy satellite nodes.
