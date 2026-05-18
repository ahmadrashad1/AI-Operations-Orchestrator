from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.auth import JWTHandler
from app.core.config import get_settings

security = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    user_id: str
    tenant_id: str
    email: str = ""
    roles: tuple[str, ...] = Field(default_factory=tuple)

    def has_any_role(self, *allowed_roles: str) -> bool:
        allowed = set(allowed_roles)
        return bool(allowed.intersection(self.roles))

    def has_all_roles(self, *required_roles: str) -> bool:
        required = set(required_roles)
        return required.issubset(set(self.roles))


def get_current_principal(
    # JWT token (preferred for production)
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    # Fallback headers for development
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
    x_roles: Annotated[str | None, Header(alias="x-roles")] = None,
) -> Principal:
    settings = get_settings()

    # Try JWT token first
    if credentials:
        try:
            jwt_handler = JWTHandler(
                app_settings=settings,
            )
            claims = jwt_handler.decode_token(credentials.credentials)
            return Principal(
                user_id=claims.user_id,
                tenant_id=claims.tenant_id,
                email=claims.email,
                roles=tuple(claims.roles),
            )
        except (ValueError, Exception) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fallback to header-based auth for development
    if settings.environment == "development":
        roles = tuple(
            part.strip() for part in (x_roles or "Admin,Manager").split(",") if part.strip()
        )
        return Principal(
            user_id=x_user_id or "local-admin",
            tenant_id=x_tenant_id or settings.default_tenant,
            email="local-admin@localhost",
            roles=roles,
        )

    # Production without JWT or headers
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )
