# ==========================================================================
# VeriQuest Backend — FastAPI Configuration
# ==========================================================================

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Environment-driven configuration. Loaded from .env file."""

    # Supabase
    supabase_url: str = "http://localhost:54321"
    supabase_service_key: str = ""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:54322/postgres"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Execution sandbox
    execution_image: str = "veriquest-icarus:latest"
    execution_timeout_ms: int = 5000
    execution_memory_mb: int = 256
    execution_cpu_limit: str = "1.0"
    execution_pids_limit: int = 64
    max_submission_bytes: int = 65536
    max_output_bytes: int = 65536

    # Application
    app_name: str = "VeriQuest"
    debug: bool = False

    # XP thresholds (centralized, changeable)
    xp_easy: int = 50
    xp_medium: int = 100
    xp_hard: int = 200

    # Level thresholds (JSON list of cumulative XP breakpoints)
    level_thresholds: str = "0,500,1000,1500,2200,3000,4000,5200,6500,8000,10000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def level_breakpoints(self) -> list[int]:
        return [int(x.strip()) for x in self.level_thresholds.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
