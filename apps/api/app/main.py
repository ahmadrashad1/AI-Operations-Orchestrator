from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.bootstrap import init_container
from app.core.config import get_settings


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run DB migrations and wire services before accepting traffic (production Postgres)."""
    init_container()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-native operational orchestration system",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "booting",
        "docs": "/docs",
    }

