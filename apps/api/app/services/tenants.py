from __future__ import annotations
from typing import List
from app.db.repositories import BaseTenantRepository


class TenantService:
    def __init__(self, tenant_repository: BaseTenantRepository):
        self.tenant_repository = tenant_repository

    def create_tenant(self, tenant_id: str, name: str) -> dict:
        tenant = {"tenant_id": tenant_id, "name": name}
        return self.tenant_repository.create_tenant(tenant)

    def list_tenants(self) -> list[dict]:
        return self.tenant_repository.list_tenants()
