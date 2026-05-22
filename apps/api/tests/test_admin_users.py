from fastapi.testclient import TestClient

from app.bootstrap import get_container
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    get_container().reset_state()


def test_create_list_update_delete_user() -> None:
    # create a user as admin
    resp = client.post(
        "/api/v1/internal/admin/users",
        headers={"x-user-id": "sysadmin", "x-roles": "Admin"},
        json={"email": "alice@example.com", "password": "s3cret", "tenant_id": "t1", "roles": ["Employee"]},
    )
    assert resp.status_code == 201
    user = resp.json()
    assert user["email"] == "alice@example.com"

    # list users for tenant
    resp = client.get(
        "/api/v1/internal/admin/tenants/t1/users",
        headers={"x-user-id": "sysadmin", "x-roles": "Admin"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["email"] == "alice@example.com" for u in users)

    # update roles
    resp = client.patch(
        f"/api/v1/internal/admin/users/{user['user_id']}/roles",
        headers={"x-user-id": "sysadmin", "x-roles": "Admin"},
        json={"roles": ["Manager"]},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert "Manager" in updated["roles"]

    # delete (disable)
    resp = client.delete(
        f"/api/v1/internal/admin/users/{user['user_id']}",
        headers={"x-user-id": "sysadmin", "x-roles": "Admin"},
    )
    assert resp.status_code == 204
