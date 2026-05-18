"""JWT encode/decode regression tests."""

from __future__ import annotations

import uuid

from app.core.auth import JWTHandler, TokenClaims


def test_access_token_roundtrip_numeric_dates() -> None:
    handler = JWTHandler(secret_key="unit-test-secret-key-minimum-32-characters")
    jti = str(uuid.uuid4())
    token = handler.create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="a@b.com",
        roles=["Manager"],
        jti=jti,
    )
    claims = handler.decode_token(token)
    assert isinstance(claims, TokenClaims)
    assert claims.user_id == "u1"
    assert claims.tenant_id == "t1"
    assert claims.email == "a@b.com"
    assert claims.roles == ["Manager"]
    assert claims.jti == jti
    assert claims.token_type == "access"


def test_token_claims_from_jwt_decode_payload() -> None:
    payload = {
        "sub": "x",
        "tenant_id": "t",
        "email": "e@e.com",
        "roles": ["Employee"],
        "jti": "j",
        "token_type": "access",
        "exp": 2_000_000_000,
        "iat": 2_000_000_000,
    }
    claims = TokenClaims.from_dict(payload)
    assert claims.exp is not None
    assert claims.exp.year >= 2030
