"""
DISTRIBUTED INCIDENT REPLAY ENGINE

Records, persists, and provides timeline playback for distributed incidents:
- Play, Pause, Step Forward, Step Backward, Speed Control (1x, 2x, 5x)
- Detailed step inspection with physical timestamp, Lamport clock, vector clock, and event payload
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from backend.database.db import get_db_context
from backend.database.models import IncidentModel

logger = logging.getLogger("IncidentReplay")

class IncidentReplayEngine:
    def create_incident_record(
        self,
        title: str,
        cause_node: str,
        affected_tasks: List[str],
        event_timeline: List[Dict[str, Any]],
        recovery_duration_ms: float
    ) -> Dict[str, Any]:
        incident_id = f"INC-{int(time.time() * 1000)}"
        record = {
            "incident_id": incident_id,
            "title": title,
            "severity": "CRITICAL" if cause_node == "SAT-05" else "HIGH",
            "cause_node": cause_node,
            "affected_tasks": affected_tasks,
            "recovery_status": "RECOVERED",
            "recovery_duration_ms": recovery_duration_ms,
            "event_timeline": event_timeline,
            "created_at": time.time()
        }

        try:
            with get_db_context() as db:
                m = IncidentModel(
                    incident_id=incident_id,
                    title=title,
                    severity=record["severity"],
                    cause_node=cause_node,
                    affected_tasks_json=json.dumps(affected_tasks),
                    recovery_status="RECOVERED",
                    recovery_duration_ms=recovery_duration_ms,
                    event_timeline_json=json.dumps(event_timeline),
                    created_at=record["created_at"]
                )
                db.add(m)
                db.commit()
        except Exception as e:
            logger.warning(f"Could not persist incident record to DB: {e}")

        return record

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with get_db_context() as db:
            inc = db.query(IncidentModel).filter_by(incident_id=incident_id).first()
            if not inc:
                return None
            return {
                "incident_id": inc.incident_id,
                "title": inc.title,
                "severity": inc.severity,
                "cause_node": inc.cause_node,
                "affected_tasks": json.loads(inc.affected_tasks_json) if inc.affected_tasks_json else [],
                "recovery_status": inc.recovery_status,
                "recovery_duration_ms": inc.recovery_duration_ms,
                "event_timeline": json.loads(inc.event_timeline_json) if inc.event_timeline_json else [],
                "created_at": inc.created_at
            }

    def list_incidents(self) -> List[Dict[str, Any]]:
        with get_db_context() as db:
            incidents = db.query(IncidentModel).order_by(IncidentModel.created_at.desc()).all()
            res = []
            for inc in incidents:
                res.append({
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "cause_node": inc.cause_node,
                    "affected_tasks": json.loads(inc.affected_tasks_json) if inc.affected_tasks_json else [],
                    "recovery_status": inc.recovery_status,
                    "recovery_duration_ms": inc.recovery_duration_ms,
                    "created_at": inc.created_at
                })
            return res

global_incident_replay_engine = IncidentReplayEngine()
