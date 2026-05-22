from fastapi.testclient import TestClient

from app.bootstrap import get_container
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    get_container().reset_state()


def _create_workflow(tenant_id: str, user_id: str, request_text: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflow/create",
        headers={
            "x-user-id": user_id,
            "x-tenant-id": tenant_id,
            "x-roles": "Employee",
        },
        json={"request_text": request_text},
    )
    assert response.status_code == 200
    return response.json()["workflow"]


def test_tenant_summary_is_scoped_to_authenticated_tenant() -> None:
    workflow_a = _create_workflow("tenant-a", "employee-a", "Need 5 laptops for the engineering team")
    _create_workflow("tenant-b", "employee-b", "Need 1 monitor for the operations team")

    response = client.get(
        "/api/v1/internal/reports/tenant-summary",
        headers={
            "x-user-id": "auditor-a",
            "x-tenant-id": "tenant-a",
            "x-roles": "Auditor",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "tenant-a"
    assert body["workflow_count"] == 1
    assert body["audit_event_count"] >= 1
    assert workflow_a["workflow_id"] in body["recent_workflow_ids"]
    assert body["recent_actions"]


def test_tenant_summary_blocks_cross_tenant_access_for_non_admins() -> None:
    _create_workflow("tenant-b", "employee-b", "Need 5 laptops for the engineering team")

    response = client.get(
        "/api/v1/internal/reports/tenant-summary?tenant_id=tenant-b",
        headers={
            "x-user-id": "auditor-a",
            "x-tenant-id": "tenant-a",
            "x-roles": "Auditor",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Reporting is limited to the authenticated tenant."
