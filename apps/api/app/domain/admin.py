from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid


def gen_id(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class User:
    user_id: str
    email: str
    hashed_password: str
    tenant_id: str | None = None
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Tenant:
    tenant_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)


def create_user_dict(email: str, hashed_password: str, tenant_id: str | None = None, roles: list[str] | None = None) -> dict:
    return {
        "user_id": gen_id("u"),
        "email": email,
        "hashed_password": hashed_password,
        "tenant_id": tenant_id,
        "roles": roles or [],
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
