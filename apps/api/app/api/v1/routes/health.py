from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, list[str] | str]:
    return {
        "status": "ready",
        "layers": [
            "api-gateway",
            "operational-core",
            "orchestration-runtime",
            "ai-services",
            "integration-registry",
        ],
    }
