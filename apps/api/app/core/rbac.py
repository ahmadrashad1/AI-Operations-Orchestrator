"""Role-based permission matrix and helper dependency.

This module provides a simple, code-driven permission matrix mapping
permissions to allowed roles and a `require_permission()` dependency
that routes can use to enforce permission checks.

The permission matrix is intentionally conservative and can be
replaced later by a DB-backed or external policy provider.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_principal, Principal
from app.bootstrap import get_container
from functools import lru_cache


# Default permission -> allowed roles mapping. Update as needed.
DEFAULT_PERMISSION_MATRIX: dict[str, list[str]] = {
    "workflow:create": ["Admin", "Manager"],
    "workflow:view": ["Admin", "Manager", "Employee", "Auditor"],
    "workflow:approve": ["Manager", "Finance"],
    "workflow:admin": ["Admin"],
    "audit:view": ["Admin", "Auditor"],
    "agent:execute": ["Admin", "Manager"],
    "event:publish": ["Admin", "Manager", "Auditor"],
    "metrics:read": ["Admin", "Manager", "Auditor"],
    "reports:view": ["Admin", "Manager", "Auditor"],
    "admin:manage": ["Admin"],
}


def get_permission_matrix() -> dict[str, list[str]]:
    """Return the active permission matrix (pluggable).

    Replace this function with a DB fetch or external policy call if
    you want dynamic permissions later.
    """
    # Try DB-backed store first (if available), otherwise fall back to defaults
    try:
        container = get_container()
        repo = getattr(container, "permission_repository", None)
        if repo:
            # Cache using lru_cache wrapper via inner helper
            return _load_permissions_from_repo(repo)
    except Exception:
        pass
    return DEFAULT_PERMISSION_MATRIX


@lru_cache(maxsize=1)
def _load_permissions_from_repo(repo) -> dict[str, list[str]]:
    try:
        return repo.list_permissions()
    except Exception:
        return DEFAULT_PERMISSION_MATRIX


def require_permission(permission: str) -> Callable[[Principal], Principal]:
    """FastAPI dependency that ensures the current principal has the
    required permission.

    Usage:
        @router.get("/...", dependencies=[Depends(require_permission("workflow:view"))])
    """

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        matrix = get_permission_matrix()
        allowed_roles = set(matrix.get(permission, []))
        if not allowed_roles:
            # Deny by default when permission is unknown
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

        if not set(principal.roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The authenticated principal does not have access to this resource.",
            )

        return principal

    return dependency
ROLE_ADMIN = "Admin"
ROLE_MANAGER = "Manager"
ROLE_EMPLOYEE = "Employee"
ROLE_COMPLIANCE = "Compliance"
ROLE_AUDITOR = "Auditor"
ROLE_FINANCE = "Finance"
