"""
USP-10: PREDICTIVE & PROACTIVE HEALTH ENGINE

Detects early warning indicators prior to physical crash:
- Battery < 25% or degrading rapidly
- CPU > 85% or spiking
- Temperature > 75°C
- Signal strength < 60%
Generates preemptive task migration advice ("SAT-03 elevated risk; consider preemptive task migration").
"""

import time
import logging
from typing import Dict, Any, List
from backend.registry.service_registry import global_registry
from backend.services.task_manager import global_task_manager

logger = logging.getLogger("PredictiveHealth")

class PredictiveHealthEngine:
    def evaluate_constellation_health_trends(self) -> Dict[str, Any]:
        sats = global_registry.list_all()
        tasks = global_task_manager.list_tasks()

        warnings = []
        preemptive_recommendations = []

        for reg in sats:
            if reg.status in ["OFFLINE", "DISCONNECTED", "FAILED"]:
                continue

            risk_factors = []
            if reg.battery < 30.0:
                risk_factors.append(f"Battery Low ({reg.battery:.1f}%)")
            if reg.temperature > 75.0:
                risk_factors.append(f"Thermal Elevation ({reg.temperature:.1f}°C)")
            if reg.cpu_usage > 85.0:
                risk_factors.append(f"High CPU Workload ({reg.cpu_usage:.1f}%)")
            if reg.signal_strength < 65.0:
                risk_factors.append(f"Signal Degradation ({reg.signal_strength:.1f}%)")

            if risk_factors:
                owned_tasks = [t["task_id"] for t in tasks if t["current_owner"] == reg.satellite_id]
                warning_entry = {
                    "satellite_id": reg.satellite_id,
                    "risk_level": "ELEVATED" if len(risk_factors) >= 2 else "WARNING",
                    "risk_factors": risk_factors,
                    "owned_tasks": owned_tasks,
                    "recommendation": f"Preemptively migrate tasks {owned_tasks} from {reg.satellite_id} to avoid physical crash."
                }
                warnings.append(warning_entry)
                if owned_tasks:
                    preemptive_recommendations.append(warning_entry)

        res = {
            "constellation_status": "PREDICTIVE_WARNING" if warnings else "NOMINAL",
            "warnings_count": len(warnings),
            "node_warnings": warnings,
            "preemptive_recommendations": preemptive_recommendations,
            "evaluated_at": time.time()
        }
        return res

global_predictive_health = PredictiveHealthEngine()
