"""Configuração central da API (12-factor, .env somente em desenvolvimento)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://factory:factory@postgres:5432/factory"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://factory:factory@rabbitmq:5672/"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "factory"
    minio_secret_key: str = "local-development-password"
    minio_bucket: str = "factory"
    minio_secure: bool = False

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_primary_model: str = "qwen2.5-coder:7b"
    ollama_fallback_model: str = "llama3.1:8b"

    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "factory-api"

    jwt_secret_key: str = "change-me-in-local-dev"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_minutes: int = 1440

    max_gate_cycles: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
