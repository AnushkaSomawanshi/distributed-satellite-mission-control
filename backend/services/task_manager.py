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
from backend.services.distributed_clocks import global_clock_manager

logger = logging.getLogger("TaskManager")

SATELLITE_CAPABILITIES = {
    "SAT-01": ["CAMERA", "RELAY", "COMPUTE"],
    "SAT-02": ["CAMERA", "THERMAL"],
    "SAT-03": ["THERMAL", "RELAY", "COMPUTE"],
    "SAT-04": ["CAMERA", "RELAY"],
    "SAT-05": ["CAMERA", "THERMAL", "RELAY", "COMPUTE"]
}

DEFAULT_TASKS = [
    {
        "task_id": "T-047",
        "mission_id": "MIS-EARTH-OBS",
        "task_type": "EARTH_OBSERVATION",
        "description": "High-resolution coastal erosion imaging over Pacific sector.",
        "priority": "HIGH",
        "required_capabilities": ["CAMERA", "COMPUTE"],
        "current_owner": "SAT-03",
        "status": "RUNNING"
    },
    {
        "task_id": "T-048",
        "mission_id": "MIS-THERMAL-SCAN",
        "task_type": "THERMAL_MAP",
        "description": "Volcanic activity monitoring & thermal anomaly detection.",
        "priority": "HIGH",
        "required_capabilities": ["THERMAL"],
        "current_owner": "SAT-02",
        "status": "RUNNING"
    },
    {
        "task_id": "T-049",
        "mission_id": "MIS-RELAY-NET",
        "task_type": "DATA_RELAY",
        "description": "Deep-space probe telemetry backhaul relay stream.",
        "priority": "MEDIUM",
        "required_capabilities": ["RELAY"],
        "current_owner": "SAT-01",
        "status": "RUNNING"
    },
    {
        "task_id": "T-050",
        "mission_id": "MIS-ORBITAL-COMPUTE",
        "task_type": "COMPUTE_ANALYTICS",
        "description": "Orbital debris trajectory prediction & collision risk processing.",
        "priority": "HIGH",
        "required_capabilities": ["COMPUTE"],
        "current_owner": "SAT-05",
        "status": "RUNNING"
    },
    {
        "task_id": "T-051",
        "mission_id": "MIS-ATMOS-RELAY",
        "task_type": "DATA_RELAY",
        "description": "Atmospheric sensor constellation aggregation.",
        "priority": "LOW",
        "required_capabilities": ["RELAY", "COMPUTE"],
        "current_owner": "SAT-04",
        "status": "RUNNING"
    }
]

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
                        clk = global_clock_manager.record_node_event(t_info["current_owner"], "TASK_INITIALIZED")
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
                            lamport_timestamp=clk["lamport_timestamp"],
                            vector_clock=json.dumps(clk["vector_clock"]),
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

    def reassign_task(self, task_id: str, new_owner: str, reason: str = "AUTONOMOUS_REALLOCATION") -> Dict[str, Any]:
        with get_db_context() as db:
            t = db.query(MissionTaskModel).filter_by(task_id=task_id).first()
            if not t:
                raise ValueError(f"Task {task_id} not found")

            prev = t.current_owner
            t.previous_owner = prev
            t.current_owner = new_owner
            t.status = "REASSIGNED"
            t.updated_at = time.time()

            clk = global_clock_manager.record_node_event(new_owner, f"TASK_REASSIGNED_{task_id}")
            t.lamport_timestamp = clk["lamport_timestamp"]
            t.vector_clock = json.dumps(clk["vector_clock"])

            db.commit()

            logger.info(f"[TASK REASSIGNMENT] Task {task_id} transferred from {prev} -> {new_owner} | Reason={reason}")

            return {
                "task_id": task_id,
                "previous_owner": prev,
                "new_owner": new_owner,
                "status": "REASSIGNED",
                "lamport_timestamp": clk["lamport_timestamp"],
                "vector_clock": clk["vector_clock"],
                "updated_at": t.updated_at
            }

    def get_capabilities_map(self) -> Dict[str, List[str]]:
        return dict(SATELLITE_CAPABILITIES)

global_task_manager = TaskManager()
