from typing import Dict, Any, Tuple

class HealthEngine:
    """
    Calculates Satellite Health Score (0.0 to 100.0) based on weighted telemetry metrics:
    - Battery level (25% weight): Optimal 70-100%
    - Temperature (25% weight): Optimal 15-45°C
    - CPU usage (20% weight): Optimal 0-75%
    - Memory usage (15% weight): Optimal 0-80%
    - Signal strength (15% weight): Optimal 60-100%
    
    Status states:
    - 90.0 to 100.0: HEALTHY
    - 70.0 to 89.9: WARNING
    - < 70.0: CRITICAL
    - Timeout / unreachable: OFFLINE
    """

    @staticmethod
    def calculate_health(
        battery: float,
        temperature: float,
        cpu_usage: float,
        memory_usage: float,
        signal_strength: float,
        is_online: bool = True
    ) -> Tuple[float, str, Dict[str, Any]]:
        if not is_online:
            return 0.0, "OFFLINE", {"reason": "Node heartbeat timeout or network drop"}

        # 1. Battery score (0-25)
        if battery >= 70:
            battery_score = 25.0
        elif battery >= 30:
            battery_score = 25.0 * (battery / 70.0)
        else:
            battery_score = 10.0 * (battery / 30.0)

        # 2. Temperature score (0-25) - Ideal 20-40 C
        if 15 <= temperature <= 45:
            temp_score = 25.0
        elif 0 <= temperature < 15:
            temp_score = 25.0 * (temperature / 15.0)
        elif 45 < temperature <= 75:
            temp_score = 25.0 * (1.0 - (temperature - 45) / 30.0)
        else:
            temp_score = 0.0

        # 3. CPU Score (0-20) - Ideal low
        if cpu_usage <= 70:
            cpu_score = 20.0
        elif cpu_usage <= 95:
            cpu_score = 20.0 * (1.0 - (cpu_usage - 70) / 25.0)
        else:
            cpu_score = 2.0

        # 4. Memory Score (0-15) - Ideal low
        if memory_usage <= 80:
            mem_score = 15.0
        else:
            mem_score = 15.0 * (1.0 - (memory_usage - 80) / 20.0)

        # 5. Signal Score (0-15) - Ideal high
        if signal_strength >= 60:
            signal_score = 15.0
        else:
            signal_score = 15.0 * (signal_strength / 60.0)

        total_score = max(0.0, min(100.0, battery_score + temp_score + cpu_score + mem_score + signal_score))

        if total_score >= 90.0:
            status = "HEALTHY"
        elif total_score >= 70.0:
            status = "WARNING"
        else:
            status = "CRITICAL"

        breakdown = {
            "battery_contrib": round(battery_score, 2),
            "temp_contrib": round(temp_score, 2),
            "cpu_contrib": round(cpu_score, 2),
            "mem_contrib": round(mem_score, 2),
            "signal_contrib": round(signal_score, 2),
            "total_score": round(total_score, 2)
        }

        return round(total_score, 2), status, breakdown
