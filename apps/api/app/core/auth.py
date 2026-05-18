"""JWT token generation and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

if TYPE_CHECKING:
    from app.core.config import Settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTConfig:
    """JWT configuration."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days


class TokenClaims:
    """JWT token claims."""

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        roles: list[str],
        jti: str,
        token_type: str = "access",
        exp: datetime | None = None,
        iat: datetime | None = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.roles = roles
        self.jti = jti
        self.token_type = token_type
        self.exp = exp or datetime.now(UTC)
        self.iat = iat or datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert claims to dictionary (Python objects)."""
        return {
            "sub": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "roles": self.roles,
            "jti": self.jti,
            "token_type": self.token_type,
            "exp": self.exp,
            "iat": self.iat,
        }

    def to_jwt_payload(self) -> dict[str, Any]:
        """JWT payload with numeric dates for python-jose."""
        exp = self.exp or datetime.now(UTC)
        iat = self.iat or datetime.now(UTC)
        return {
            "sub": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "roles": self.roles,
            "jti": self.jti,
            "token_type": self.token_type,
            "exp": int(exp.timestamp()),
            "iat": int(iat.timestamp()),
        }

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=UTC)
        raise ValueError("Invalid datetime claim")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenClaims:
        """Create claims from dictionary (decode handles JWT numeric dates)."""
        roles_raw = data.get("roles", [])
        roles = list(roles_raw) if isinstance(roles_raw, (list, tuple)) else []
        exp = cls._parse_dt(data.get("exp"))
        iat = cls._parse_dt(data.get("iat"))
        return cls(
            user_id=data.get("sub", ""),
            tenant_id=data.get("tenant_id", ""),
            email=data.get("email", ""),
            roles=roles,
            jti=data.get("jti", ""),
            token_type=data.get("token_type", "access"),
            exp=exp,
            iat=iat,
        )


class JWTHandler:
    """JWT token handling."""

    def __init__(
        self,
        app_settings: Settings | None = None,
        secret_key: str = "dev-secret-change-in-production",
    ):
        # If settings provided, use from there; otherwise use provided secret_key
        if app_settings:
            self.secret_key = app_settings.jwt_secret_key
            self.algorithm = "HS256"
            self.access_token_expire_minutes = app_settings.jwt_access_token_expire_minutes
            self.refresh_token_expire_days = app_settings.jwt_refresh_token_expire_days
        else:
            self.secret_key = secret_key
            self.algorithm = "HS256"
            self.access_token_expire_minutes = 60
            self.refresh_token_expire_days = 7

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        roles: list[str],
        jti: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.now(UTC)
        exp = now + expires_delta

        claims = TokenClaims(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            roles=roles,
            jti=jti,
            token_type="access",
            exp=exp,
            iat=now,
        )

        return jwt.encode(claims.to_jwt_payload(), self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        roles: list[str],
        jti: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.now(UTC)
        exp = now + expires_delta

        claims = TokenClaims(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            roles=roles,
            jti=jti,
            token_type="refresh",
            exp=exp,
            iat=now,
        )

        return jwt.encode(claims.to_jwt_payload(), self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> TokenClaims:
        """Decode and validate token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            claims = TokenClaims.from_dict(payload)
            if claims.exp is not None and claims.exp < datetime.now(UTC):
                raise ValueError("Token expired")
            return claims
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")

    def verify_token_type(self, claims: TokenClaims, expected_type: str) -> bool:
        """Verify token type."""
        return claims.token_type == expected_type


def hash_password(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return pwd_context.verify(plain_password, hashed_password)
