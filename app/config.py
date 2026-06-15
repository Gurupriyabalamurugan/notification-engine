from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "notification-engine"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://notification:notification@localhost:5432/notification_engine"
    )

    redis_url: str = "redis://localhost:6379/0"
    idempotency_ttl_seconds: int = 86400

    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_client_id: str = "notification-engine"
    kafka_consumer_group: str = "notification-dispatcher"
    kafka_topic_partitions: int = 12

    mock_email_failure_rate: float = 0.0
    mock_email_down: bool = False
    mock_email_latency_ms: int = 0

    mock_sms_failure_rate: float = 0.0
    mock_sms_down: bool = False
    mock_sms_latency_ms: int = 0

    mock_push_failure_rate: float = 0.0
    mock_push_down: bool = False
    mock_push_latency_ms: int = 0

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_open_seconds: int = 60

    retry_backoff_seconds: list[int] = [30, 120, 600, 1800, 7200]
    retry_worker_poll_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
