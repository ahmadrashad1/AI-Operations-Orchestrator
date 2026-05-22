import os
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine

from app.db.migrations import run_migrations
from app.db.postgres import PostgresUserRepository


def test_postgres_user_repository_crud():
    with PostgresContainer("postgres:15") as postgres:
        # Build SQLAlchemy URL with psycopg driver
        url = postgres.get_connection_url()
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        os.environ["APP_DATABASE_URL"] = url

        engine = create_engine(url)

        # Create only the users table from SQLAlchemy models for testing
        from app.db.models import UserModel

        UserModel.__table__.create(engine)

        repo = PostgresUserRepository(engine)

        # Create user
        user = {
            "user_id": "u_test",
            "email": "bob@example.com",
            "tenant_id": "t_test",
            "hashed_password": "pw",
            "roles": ["Employee"],
            "is_active": True,
        }
        created = repo.create_user(user)
        assert created["email"] == "bob@example.com"

        # Get user
        got = repo.get_user(created["user_id"]) or repo.get_user("u_test")
        assert got is not None and got["email"] == "bob@example.com"

        # List users by tenant
        listed = repo.list_users(tenant_id="t_test")
        assert any(u["email"] == "bob@example.com" for u in listed)

        # Update roles
        updated = repo.update_user(created["user_id"], {"roles": ["Manager"]})
        assert "Manager" in updated["roles"]

        # Delete user
        repo.delete_user(created["user_id"])
        assert repo.get_user(created["user_id"]) is None
