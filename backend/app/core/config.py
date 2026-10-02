# ==========================================================================
# VeriQuest Backend — FastAPI Configuration
# ==========================================================================

from pydantic_settings import BaseSettings
from functools import lru_cache
from urllib.parse import urlsplit
from pydantic import field_validator, SecretStr
from .database_config import validate_database_url


class Settings(BaseSettings):
    """Environment-driven configuration. Loaded from .env file."""

    # Supabase
    supabase_url: str = "http://localhost:54321"
    supabase_service_key: str = ""
    # Issuer identity is independent of the network route used to fetch keys.
    jwt_issuer: str = "http://127.0.0.1:54321/auth/v1"
    jwt_jwks_url: str = "http://127.0.0.1:54321/auth/v1/.well-known/jwks.json"
    jwt_algorithms: str = "ES256"
    jwt_audience: str = "authenticated"
    jwt_clock_tolerance_seconds: int = 30

    @field_validator("jwt_algorithms")
    @classmethod
    def validate_algorithms(cls, value: str) -> str:
        algorithms = value.split(",")
        if any(a not in {"ES256", "RS256"} for a in algorithms) or len(set(algorithms)) != len(algorithms):
            raise ValueError("JWT algorithms must be an explicit unique ES256/RS256 allow-list")
        return value

    @field_validator("jwt_issuer", "jwt_jwks_url")
    @classmethod
    def validate_auth_url(cls, value: str) -> str:
        url = urlsplit(value)
        if value != value.strip() or url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("JWT URLs must be explicit HTTP(S) URLs without credentials/query/fragment")
        return value

    @field_validator("jwt_audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("JWT audience must be nonempty")
        return value

    @field_validator("jwt_clock_tolerance_seconds")
    @classmethod
    def validate_tolerance(cls, value: int) -> int:
        if not 0 <= value <= 60:
            raise ValueError("JWT clock tolerance must be between 0 and 60 seconds")
        return value

    # Database
    database_url: SecretStr

    @field_validator('database_url')
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        validate_database_url(value.get_secret_value())
        return value

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    # API publisher and worker use REDIS_URL; never infer transport from JWT URLs.
    task_publish_timeout_seconds: int = 2

    @field_validator("redis_url")
    @classmethod
    def validate_broker(cls, value: str) -> str:
        url = urlsplit(value)
        if value != value.strip() or url.scheme not in {"redis", "rediss"} or not url.hostname or url.query or url.fragment:
            raise ValueError("Redis transport must be an explicit redis/rediss endpoint")
        return value

    @field_validator("task_publish_timeout_seconds")
    @classmethod
    def validate_publish_timeout(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("Task publication timeout must be between 1 and 5 seconds")
        return value

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "hide_input_in_errors": True, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
