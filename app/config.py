"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./payout_engine.db"
    log_level: str = "INFO"
    mock_failure_rate: float = 0.05  # 5% simulated failure rate
    mock_latency_ms: int = 100  # Simulated provider latency

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
