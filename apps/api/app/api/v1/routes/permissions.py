from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any

from app.api.dependencies import get_permission_repository
from app.api.dependencies import require_permission_dep

router = APIRouter(prefix="/permissions")


@router.get("/", response_model=dict)
def list_permissions(repo=Depends(get_permission_repository)) -> dict[str, Any]:
    return repo.list_permissions()


class PermissionUpsertRequest(dict):
    pass


@router.post("/", dependencies=[Depends(require_permission_dep("workflow:admin"))])
def upsert_permission(payload: dict, repo=Depends(get_permission_repository)) -> dict:
    permission = payload.get("permission")
    roles = payload.get("roles", [])
    description = payload.get("description")
    repo.upsert_permission(permission, roles, description)
    return {"ok": True}
