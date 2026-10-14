"""
MISSION TASK MANAGER SERVICE

Manages first-class MissionTask objects, satellite capabilities mapping,
task capability matching, task state transitions, and seeding initial tasks.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from backend.database.db import get_db_context
from backend.database.models import MissionModel, MissionTaskModel

logger = logging.getLogger("TaskManager")

from backend.fa2_extensions.catalog import MISSION_TASKS, SATELLITE_CAPABILITIES  # shared with the satellites

# Seed rows only; afterwards this table MIRRORS ownership reported by the satellites (they own the tasks).
DEFAULT_TASKS = [{**{k: v for k, v in t.items() if k != "initial_owner"},
                  "current_owner": t["initial_owner"], "status": "RUNNING"} for t in MISSION_TASKS]

class TaskManager:
    def __init__(self):
        self._initialize_seed_tasks()

    def _initialize_seed_tasks(self):
        try:
            with get_db_context() as db:
                existing_mission = db.query(MissionModel).filter_by(mission_id="MIS-ORBITAL-PRIMARY").first()
                if not existing_mission:
                    m = MissionModel(
                        mission_id="MIS-ORBITAL-PRIMARY",
                        name="Constellation Earth & Space Operations",
                        description="Primary autonomous distributed satellite observation mission.",
                        status="ACTIVE"
                    )
                    db.add(m)
                    db.commit()

                for t_info in DEFAULT_TASKS:
                    t_model = db.query(MissionTaskModel).filter_by(task_id=t_info["task_id"]).first()
                    if not t_model:
                        t_model = MissionTaskModel(
                            task_id=t_info["task_id"],
                            mission_id=t_info["mission_id"],
                            task_type=t_info["task_type"],
                            description=t_info["description"],
                            priority=t_info["priority"],
                            required_capabilities=json.dumps(t_info["required_capabilities"]),
                            current_owner=t_info["current_owner"],
                            previous_owner=None,
                            status=t_info["status"],
                            lamport_timestamp=0,
                            vector_clock=json.dumps({}),
                            created_at=time.time(),
                            updated_at=time.time()
                        )
                        db.add(t_model)
                db.commit()
        except Exception as e:
            logger.warning(f"Task seed initialization fallback: {e}")

    def list_tasks(self) -> List[Dict[str, Any]]:
        with get_db_context() as db:
            tasks = db.query(MissionTaskModel).all()
            res = []
            for t in tasks:
                res.append({
                    "task_id": t.task_id,
                    "mission_id": t.mission_id,
                    "task_type": t.task_type,
                    "description": t.description,
                    "priority": t.priority,
                    "required_capabilities": json.loads(t.required_capabilities) if isinstance(t.required_capabilities, str) else t.required_capabilities,
                    "current_owner": t.current_owner,
                    "previous_owner": t.previous_owner,
                    "status": t.status,
                    "lamport_timestamp": t.lamport_timestamp,
                    "vector_clock": json.loads(t.vector_clock) if t.vector_clock else {},
                    "created_at": t.created_at,
                    "updated_at": t.updated_at
                })
            return res

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with get_db_context() as db:
            t = db.query(MissionTaskModel).filter_by(task_id=task_id).first()
            if not t:
                return None
            return {
                "task_id": t.task_id,
                "mission_id": t.mission_id,
                "task_type": t.task_type,
                "description": t.description,
                "priority": t.priority,
                "required_capabilities": json.loads(t.required_capabilities) if isinstance(t.required_capabilities, str) else t.required_capabilities,
                "current_owner": t.current_owner,
                "previous_owner": t.previous_owner,
                "status": t.status,
                "lamport_timestamp": t.lamport_timestamp,
                "vector_clock": json.loads(t.vector_clock) if t.vector_clock else {},
                "created_at": t.created_at,
                "updated_at": t.updated_at
            }

    def mirror(self, task_id: str, owner: str, status: str, version: Optional[int] = None) -> None:
        """Record ownership as reported by the satellites (no decision is taken here)."""
        with get_db_context() as db:
            t = db.query(MissionTaskModel).filter_by(task_id=task_id).first()
            if not t or (t.current_owner == owner and t.status == status):
                return
            if t.current_owner != owner:
                t.previous_owner = t.current_owner
                t.current_owner = owner
            t.status = status
            t.updated_at = time.time()
            db.commit()

    def get_capabilities_map(self) -> Dict[str, List[str]]:
        return dict(SATELLITE_CAPABILITIES)

global_task_manager = TaskManager()
