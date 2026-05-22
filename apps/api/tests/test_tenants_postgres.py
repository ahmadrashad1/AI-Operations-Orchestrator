import os
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine

from app.db.postgres import PostgresTenantRepository


def test_postgres_tenant_repository_crud():
    with PostgresContainer("postgres:15") as postgres:
        url = postgres.get_connection_url()
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        os.environ["APP_DATABASE_URL"] = url
        engine = create_engine(url)

        # Create tenants table only for test to avoid running full migrations
        from app.db.models import TenantModel

        TenantModel.__table__.create(engine)

        repo = PostgresTenantRepository(engine)

        created = repo.create_tenant({"tenant_id": "t1", "name": "Tenant One"})
        assert created["tenant_id"] == "t1"

        listed = repo.list_tenants()
        assert any(t["tenant_id"] == "t1" for t in listed)
