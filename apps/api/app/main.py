from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.v1.router import api_router
from app.bootstrap import get_container, init_container
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run DB migrations and wire services before accepting traffic (production Postgres)."""
    container = init_container()
    _app.state.metrics_collector = container.metrics_collector
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-native operational orchestration system",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    start = perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid4())
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (perf_counter() - start) * 1000.0
        metrics_collector = getattr(app.state, "metrics_collector", None) or get_container().metrics_collector
        if metrics_collector is not None:
            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code if response is not None else 500,
                duration_ms=duration_ms,
                request_id=request_id,
            )
        if response is not None:
            response.headers.setdefault("x-request-id", request_id)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "booting",
        "docs": "/docs",
    }
