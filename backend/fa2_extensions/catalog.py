"""
Mission task catalog shared by the satellites (which OWN and move the tasks) and Mission Control
(which only mirrors them). One definition, so both sides agree on capabilities and requirements.
"""

from typing import Any, Dict, List

SATELLITE_CAPABILITIES: Dict[str, List[str]] = {
    "SAT-01": ["CAMERA", "RELAY", "COMPUTE"],
    "SAT-02": ["CAMERA", "THERMAL"],
    "SAT-03": ["THERMAL", "RELAY", "COMPUTE"],
    "SAT-04": ["CAMERA", "RELAY"],
    "SAT-05": ["CAMERA", "THERMAL", "RELAY", "COMPUTE"],
}

# Initial owners satisfy each task's required capabilities.
MISSION_TASKS: List[Dict[str, Any]] = [
    {"task_id": "T-047", "mission_id": "MIS-EARTH-OBS", "task_type": "EARTH_OBSERVATION",
     "description": "High-resolution coastal erosion imaging over Pacific sector.",
     "priority": "HIGH", "required_capabilities": ["CAMERA", "COMPUTE"], "initial_owner": "SAT-01"},
    {"task_id": "T-048", "mission_id": "MIS-THERMAL-SCAN", "task_type": "THERMAL_MAP",
     "description": "Volcanic activity monitoring & thermal anomaly detection.",
     "priority": "HIGH", "required_capabilities": ["THERMAL"], "initial_owner": "SAT-02"},
    {"task_id": "T-049", "mission_id": "MIS-RELAY-NET", "task_type": "DATA_RELAY",
     "description": "Deep-space probe telemetry backhaul relay stream.",
     "priority": "MEDIUM", "required_capabilities": ["RELAY"], "initial_owner": "SAT-04"},
    {"task_id": "T-050", "mission_id": "MIS-ORBITAL-COMPUTE", "task_type": "COMPUTE_ANALYTICS",
     "description": "Orbital debris trajectory prediction & collision risk processing.",
     "priority": "HIGH", "required_capabilities": ["COMPUTE"], "initial_owner": "SAT-05"},
    {"task_id": "T-051", "mission_id": "MIS-ATMOS-RELAY", "task_type": "DATA_RELAY",
     "description": "Atmospheric sensor constellation aggregation.",
     "priority": "LOW", "required_capabilities": ["RELAY", "COMPUTE"], "initial_owner": "SAT-03"},
]

TASKS_BY_ID: Dict[str, Dict[str, Any]] = {t["task_id"]: t for t in MISSION_TASKS}

PRIORITY_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}


def capable(satellite_id: str, task: Dict[str, Any]) -> bool:
    caps = set(SATELLITE_CAPABILITIES.get(satellite_id, []))
    return set(task.get("required_capabilities", [])) <= caps


def suitability(satellite_id: str, task: Dict[str, Any], health: float, battery: float,
                signal: float, load: int) -> Dict[str, Any]:
    """Transparent candidate score used by the leader when it reassigns a task.

    30% health + 25% capability match + 20% battery + 15% link quality + 10% spare capacity.
    Ineligible (score 0) if the satellite lacks a required capability.
    """
    if not capable(satellite_id, task):
        return {"satellite_id": satellite_id, "eligible": False, "total_score": 0.0,
                "reason": "missing required capability"}
    caps = SATELLITE_CAPABILITIES.get(satellite_id, [])
    match = len(set(task["required_capabilities"]) & set(caps)) / max(1, len(task["required_capabilities"]))
    parts = {
        "health": 0.30 * max(0.0, min(100.0, health)),
        "capability": 0.25 * 100.0 * match,
        "battery": 0.20 * max(0.0, min(100.0, battery)),
        "link": 0.15 * max(0.0, min(100.0, signal)),
        "capacity": 0.10 * 100.0 / (1 + load),
    }
    return {"satellite_id": satellite_id, "eligible": True,
            "total_score": round(sum(parts.values()), 2), "components": {k: round(v, 2) for k, v in parts.items()}}
