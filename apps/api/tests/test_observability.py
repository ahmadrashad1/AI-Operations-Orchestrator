from fastapi.testclient import TestClient

from app.bootstrap import get_container
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    get_container().reset_state()


def test_internal_metrics_report_recent_requests() -> None:
    health_response = client.get(
        "/api/v1/healthz",
        headers={
            "x-user-id": "auditor-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Auditor",
        },
    )
    assert health_response.status_code == 200
    assert health_response.headers.get("x-request-id")

    metrics_response = client.get(
        "/api/v1/internal/metrics",
        headers={
            "x-user-id": "auditor-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Auditor",
        },
    )

    assert metrics_response.status_code == 200
    body = metrics_response.json()
    assert body["total_requests"] >= 1
    assert body["requests_by_method"]["GET"] >= 1
    assert "/api/v1/healthz" in body["requests_by_path"]
    assert body["recent_requests"]


def test_prometheus_metrics_exposition() -> None:
    # ensure the prometheus-format endpoint is exposed and contains expected metrics
    response = client.get(
        "/api/v1/internal/metrics/prometheus",
        headers={
            "x-user-id": "auditor-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Auditor",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/plain")
    text = response.text
    assert "aiops_total_requests" in text
    assert "aiops_requests_by_method" in text
