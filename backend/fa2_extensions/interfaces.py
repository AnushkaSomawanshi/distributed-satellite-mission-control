"""
FA-2 DISTRIBUTED SYSTEMS EXTENSION INTERFACES

This module defines clean abstract base classes and interfaces reserved for FA-2 extensions:
1. Lamport Timestamps
2. Vector Clock Synchronization
3. Leader Election (Bully / Ring algorithms)
4. Distributed Mutual Exclusion (Ricart-Agrawala / Maekawa)
5. Global State & Chandy-Lamport Snapshots
6. Autonomous Task Redistribution
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ILamportClock(ABC):
    @abstractmethod
    def increment(self) -> int:
        """Increment local Lamport timestamp prior to an event."""
        pass

    @abstractmethod
    def update(self, received_timestamp: int) -> int:
        """Update local clock on receiving a message with timestamp T: L_local = max(L_local, T) + 1."""
        pass

class IVectorClock(ABC):
    @abstractmethod
    def increment(self, node_id: str) -> Dict[str, int]:
        """Increment local clock component for node_id."""
        pass

    @abstractmethod
    def merge(self, received_vector: Dict[str, int]) -> Dict[str, int]:
        """Element-wise maximum merge with received vector clock."""
        pass

class ILeaderElection(ABC):
    @abstractmethod
    def start_election(self) -> str:
        """Trigger leader election algorithm (Bully / Ring). Returns new Leader Node ID."""
        pass

    @abstractmethod
    def get_leader(self) -> Optional[str]:
        """Get current elected leader node ID."""
        pass

class IDistributedMutex(ABC):
    @abstractmethod
    def request_critical_section(self, resource_id: str) -> bool:
        """Request permission to enter critical section."""
        pass

    @abstractmethod
    def release_critical_section(self, resource_id: str) -> bool:
        """Release lock on critical section."""
        pass

class IGlobalStateSnapshot(ABC):
    @abstractmethod
    def take_snapshot(self) -> Dict[str, Any]:
        """Record consistent global state snapshot across all nodes (Chandy-Lamport)."""
        pass

class ITaskScheduler(ABC):
    @abstractmethod
    def redistribute_tasks(self, failed_node_id: str, active_nodes: List[str]) -> Dict[str, List[str]]:
        """Autonomous task redistribution upon node failure."""
        pass
