from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_user_repository
from app.core.auth import JWTHandler, verify_password
from app.core.config import get_settings
from app.db.postgres import PostgresUserRepository
from app.domain.schemas import LoginRequest, RefreshTokenRequest, TokenPairResponse

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    user_repository: PostgresUserRepository = Depends(get_user_repository),
) -> TokenPairResponse:
    settings = get_settings()
    user = user_repository.get_by_email(payload.email)
    if user is None or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if user.is_active != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active.",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    roles = list(user.roles or [])
    handler = JWTHandler(app_settings=settings)
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    access_token = handler.create_access_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        roles=roles,
        jti=access_jti,
    )
    refresh_token = handler.create_refresh_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        roles=roles,
        jti=refresh_jti,
    )
    expires_in = settings.jwt_access_token_expire_minutes * 60
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/token/refresh", response_model=TokenPairResponse)
def refresh_tokens(
    payload: RefreshTokenRequest,
    user_repository: PostgresUserRepository = Depends(get_user_repository),
) -> TokenPairResponse:
    settings = get_settings()
    handler = JWTHandler(app_settings=settings)
    try:
        claims = handler.decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if not handler.verify_token_type(claims, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    user = user_repository.get_by_email(claims.email)
    if user is None or user.is_active != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer valid.",
        )

    roles = list(user.roles or [])
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    access_token = handler.create_access_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        roles=roles,
        jti=access_jti,
    )
    refresh_token = handler.create_refresh_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        roles=roles,
        jti=refresh_jti,
    )
    expires_in = settings.jwt_access_token_expire_minutes * 60
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
