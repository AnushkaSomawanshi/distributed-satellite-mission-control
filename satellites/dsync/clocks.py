"""
Clocks owned by ONE satellite process (FA-2, Unit 3).

- PhysicalClock: the satellite's own wall clock = true time + offset + drift. Offset and drift are
  injected by the CLOCK_DRIFT fault, so clock-synchronisation algorithms have something real to fix.
- LamportClock: scalar logical clock, L = max(L, received) + 1.
- VectorClock: one entry per satellite, element-wise max on receive.

Ground truth: every process in this project runs on one host (Docker or local), so `time.time()`
is a common reference. Satellites report their true skew next to their own readings; the
algorithms themselves only ever use their own clock and the messages they receive.
"""

import time
from typing import Callable, Dict, Iterable, Optional

try:  # FA-1 reserved these interfaces for FA-2; implement them when the backend package is present.
    from backend.fa2_extensions.interfaces import ILamportClock, IVectorClock
except Exception:  # pragma: no cover - satellites can run without the backend package
    ILamportClock = object  # type: ignore
    IVectorClock = object  # type: ignore


class PhysicalClock:
    def __init__(self, offset_ms: float = 0.0, drift_ppm: float = 0.0, real: Callable[[], float] = time.time):
        self._real = real
        self._offset_s = offset_ms / 1000.0
        self._drift_ppm = drift_ppm
        self._anchor = real()

    def now(self) -> float:
        """This satellite's reading of the time (seconds since epoch)."""
        r = self._real()
        return r + self._offset_s + (r - self._anchor) * self._drift_ppm * 1e-6

    def true_time(self) -> float:
        return self._real()

    def skew_ms(self) -> float:
        """How far this clock is from true time right now (positive = ahead)."""
        return (self.now() - self._real()) * 1000.0

    @property
    def drift_ppm(self) -> float:
        return self._drift_ppm

    def _rebase(self) -> None:
        # Fold the drift accumulated so far into the offset, then restart drift from now.
        r = self._real()
        self._offset_s = self.now() - r
        self._anchor = r

    def adjust(self, delta_s: float) -> None:
        """Step the clock by delta_s seconds (what a synchronisation algorithm does)."""
        self._rebase()
        self._offset_s += delta_s

    def inject_fault(self, offset_jump_ms: float = 0.0, drift_ppm: Optional[float] = None) -> None:
        """CLOCK_DRIFT fault: jump the clock by offset_jump_ms and/or change its drift rate."""
        self._rebase()
        self._offset_s += offset_jump_ms / 1000.0
        if drift_ppm is not None:
            self._drift_ppm = drift_ppm

    def reset(self) -> None:
        self._offset_s = 0.0
        self._drift_ppm = 0.0
        self._anchor = self._real()

    def to_dict(self) -> Dict[str, float]:
        return {
            "reading": self.now(),
            "true_time": self._real(),
            "skew_ms": round(self.skew_ms(), 3),
            "drift_ppm": self._drift_ppm,
        }


class LamportClock(ILamportClock):
    def __init__(self, value: int = 0):
        self.value = value

    def increment(self) -> int:
        self.value += 1
        return self.value

    def update(self, received_timestamp: int) -> int:
        self.value = max(self.value, int(received_timestamp)) + 1
        return self.value


class VectorClock(IVectorClock):
    def __init__(self, owner: str, nodes: Iterable[str] = ()):
        self.owner = owner
        self.clock: Dict[str, int] = {n: 0 for n in nodes}
        self.clock.setdefault(owner, 0)

    def increment(self, node_id: Optional[str] = None) -> Dict[str, int]:
        node_id = node_id or self.owner
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
        return dict(self.clock)

    def merge(self, received_vector: Dict[str, int]) -> Dict[str, int]:
        for node, val in received_vector.items():
            self.clock[node] = max(self.clock.get(node, 0), int(val))
        return dict(self.clock)

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    @staticmethod
    def compare(v1: Dict[str, int], v2: Dict[str, int]) -> str:
        """BEFORE (v1 -> v2), AFTER (v2 -> v1), EQUAL, or CONCURRENT (v1 || v2)."""
        less = greater = False
        for node in set(v1) | set(v2):
            a, b = v1.get(node, 0), v2.get(node, 0)
            if a < b:
                less = True
            elif a > b:
                greater = True
        if less and not greater:
            return "BEFORE"
        if greater and not less:
            return "AFTER"
        if not less and not greater:
            return "EQUAL"
        return "CONCURRENT"
