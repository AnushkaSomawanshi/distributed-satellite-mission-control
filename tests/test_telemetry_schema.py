import unittest
from pydantic import ValidationError

from backend.models.schemas import HeartbeatRequest, TelemetryObservation


class TelemetrySchemaTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            "satellite_id": "SAT-01",
            "battery": 91.5,
            "temperature": 24.2,
            "cpu_usage": 18.0,
            "memory_usage": 35.0,
            "signal_strength": 97.0,
        }

    def test_valid_observation_is_accepted(self):
        observation = TelemetryObservation(**self.valid)
        self.assertEqual(observation.satellite_id, "SAT-01")
        self.assertEqual(observation.battery, 91.5)

    def test_missing_measurement_is_rejected(self):
        payload = dict(self.valid)
        payload.pop("battery")
        with self.assertRaises(ValidationError):
            TelemetryObservation(**payload)

    def test_out_of_range_measurement_is_rejected(self):
        payload = dict(self.valid, battery=140)
        with self.assertRaises(ValidationError):
            TelemetryObservation(**payload)

    def test_heartbeat_does_not_fill_missing_measurements(self):
        payload = dict(self.valid)
        payload.pop("temperature")
        with self.assertRaises(ValidationError):
            HeartbeatRequest(**payload)

    def test_invalid_cpu_range_is_rejected(self):
        payload = dict(self.valid, cpu_usage=-1)
        with self.assertRaises(ValidationError):
            TelemetryObservation(**payload)


if __name__ == "__main__":
    unittest.main()
