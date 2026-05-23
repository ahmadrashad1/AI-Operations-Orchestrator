from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Operations Orchestrator"
    api_prefix: str = "/api/v1"
    environment: str = Field(default="development", alias="APP_ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+psycopg://orchestrator:orchestrator@localhost:5432/orchestrator",
        alias="APP_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="APP_REDIS_URL")
    default_tenant: str = Field(default="demo-tenant", alias="APP_DEFAULT_TENANT")
    tenant_header: str = "x-tenant-id"
    manager_approval_threshold: float = 3000.0
    finance_approval_threshold: float = 5000.0
    slack_webhook_url: str = Field(default="https://example.invalid/webhook", alias="APP_SLACK_WEBHOOK_URL")
    # JWT configuration
    jwt_secret_key: str = Field(default="dev-secret-change-in-production", alias="APP_JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    # Metrics and tracing
    metrics_port: int = Field(default=9187, alias="APP_METRICS_PORT")
    enable_prometheus_server: bool = Field(default=True, alias="APP_ENABLE_PROMETHEUS")
    enable_tracing: bool = Field(default=False, alias="APP_ENABLE_TRACING")
    jaeger_agent_url: str | None = Field(default=None, alias="APP_JAEGER_AGENT_URL")
    otlp_endpoint: str | None = Field(default=None, alias="APP_OTLP_ENDPOINT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

