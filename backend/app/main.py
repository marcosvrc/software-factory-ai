"""Factory API — camada de API da fábrica de software (FastAPI)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.messaging.rabbitmq import publisher
from app.observability.otel import instrument_fastapi, setup_tracing
from shared.logging import configure_logging, get_logger

logger = get_logger("factory.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    setup_tracing(settings.otel_service_name)
    try:
        await publisher.connect()
        logger.info("rabbitmq_connected")
    except Exception:  # noqa: BLE001
        logger.warning("rabbitmq_unavailable_at_startup")
    yield
    await publisher.close()


app = FastAPI(
    title="Software Factory API",
    version="0.1.0",
    description="API da fábrica de software local multiagente.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
instrument_fastapi(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
