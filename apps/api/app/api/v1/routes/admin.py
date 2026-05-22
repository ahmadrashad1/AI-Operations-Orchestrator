from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.api.dependencies import get_user_service, require_roles, get_connector_registry

router = APIRouter()


@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: dict, admin=Depends(require_roles("Admin")), svc=Depends(get_user_service)):
    if "email" not in payload or "password" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email and password are required")
    user = svc.create_user(email=payload["email"], password=payload["password"], tenant_id=payload.get("tenant_id"), roles=payload.get("roles"))
    return user


@router.get("/admin/tenants/{tenant_id}/users", response_model=List[dict])
def list_users_for_tenant(tenant_id: str, principal=Depends(require_roles("Admin", "Manager")), svc=Depends(get_user_service)):
    # Admins can list any tenant; Managers assumed to be tenant-scoped in higher checks
    users = svc.list_users(tenant_id=tenant_id)
    return users


@router.patch("/admin/users/{user_id}/roles")
def update_roles(user_id: str, payload: dict, admin=Depends(require_roles("Admin")), svc=Depends(get_user_service)):
    roles = payload.get("roles")
    if roles is None or not isinstance(roles, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="roles must be provided as a list")
    user = svc.update_user_roles(user_id, roles)
    return user


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, admin=Depends(require_roles("Admin")), svc=Depends(get_user_service)):
    svc.disable_user(user_id)
    return None


@router.post("/admin/tenants", status_code=status.HTTP_201_CREATED)
def create_tenant(payload: dict, admin=Depends(require_roles("Admin"))):
    if "tenant_id" not in payload or "name" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id and name are required")
    # store in container's in-memory tenant store
    from app.bootstrap import get_container

    container = get_container()
    tenants = getattr(container, "tenant_store", None)
    if tenants is None:
        tenants = {}
        setattr(container, "tenant_store", tenants)
    tenants[payload["tenant_id"]] = {"tenant_id": payload["tenant_id"], "name": payload["name"]}
    return tenants[payload["tenant_id"]]


@router.get("/admin/tenants", response_model=List[dict])
def list_tenants(admin=Depends(require_roles("Admin"))):
    from app.bootstrap import get_container

    container = get_container()
    tenants = getattr(container, "tenant_store", {})
    return list(tenants.values())


@router.get("/admin/connectors")
def list_connectors(admin=Depends(require_roles("Admin")), registry=Depends(get_connector_registry)):
    return {"connectors": [c.__class__.__name__ if hasattr(c, '__class__') else str(c) for c in registry.connectors]}


@router.post("/admin/connectors/register")
def register_connector(payload: dict, admin=Depends(require_roles("Admin")), registry=Depends(get_connector_registry)):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    # For now, register the payload as a placeholder connector entry
    registry.connectors.append(payload)
    return {"status": "registered", "name": name}
