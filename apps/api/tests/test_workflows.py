from fastapi.testclient import TestClient

from app.bootstrap import get_container
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    get_container().reset_state()


def test_create_workflow_requires_manager_and_finance_approval() -> None:
    response = client.post(
        "/api/v1/workflow/create",
        headers={
            "x-user-id": "employee-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Employee",
        },
        json={
            "request_text": "Need 5 laptops for the engineering team",
        },
    )

    assert response.status_code == 200
    workflow = response.json()["workflow"]

    assert workflow["tenant_id"] == "tenant-a"
    assert workflow["status"] == "waiting_approval"
    assert workflow["extraction"]["estimated_cost"] == 7000.0
    assert [approval["role"] for approval in workflow["approvals"]] == ["Manager", "Finance"]


def test_approvals_complete_workflow_after_all_required_responses() -> None:
    create_response = client.post(
        "/api/v1/workflow/create",
        headers={
            "x-user-id": "employee-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Employee",
        },
        json={
            "request_text": "Need 5 laptops for the engineering team",
        },
    )
    workflow = create_response.json()["workflow"]
    manager_approval = workflow["approvals"][0]
    finance_approval = workflow["approvals"][1]

    manager_response = client.post(
        "/api/v1/approval/respond",
        headers={
            "x-user-id": "manager-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Manager",
        },
        json={
            "workflow_id": workflow["workflow_id"],
            "approval_id": manager_approval["approval_id"],
            "decision": "approved",
        },
    )
    assert manager_response.status_code == 200
    assert manager_response.json()["workflow"]["status"] == "waiting_approval"

    finance_response = client.post(
        "/api/v1/approval/respond",
        headers={
            "x-user-id": "finance-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "Finance",
        },
        json={
            "workflow_id": workflow["workflow_id"],
            "approval_id": finance_approval["approval_id"],
            "decision": "approved",
        },
    )

    assert finance_response.status_code == 200
    assert finance_response.json()["workflow"]["status"] == "completed"
