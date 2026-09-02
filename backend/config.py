import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Distributed Satellite Constellation Health Engine"
    API_V1_STR: str = "/api"
    
    # Network / Ports
    MISSION_CONTROL_PORT: int = int(os.getenv("PORT", "8000"))
    
    # Infrastructure Services
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./satellite_system.db")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    
    # Dynamic Registry settings
    HEARTBEAT_TIMEOUT_SECONDS: float = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "10.0"))
    SWEEP_INTERVAL_SECONDS: float = float(os.getenv("SWEEP_INTERVAL_SECONDS", "3.0"))
    
    # Network simulation defaults
    DEFAULT_LATENCY_MS: float = 0.0
    DEFAULT_PACKET_LOSS_PCT: float = 0.0

    class Config:
        case_sensitive = True

settings = Settings()
