#!/usr/bin/env python3
"""Create or update a user row for JWT login (PostgreSQL).

Run inside the API container (recommended):

  docker compose exec api python scripts/seed_admin.py --email admin@demo.local --password 'YourPassword'

Or locally with APP_DATABASE_URL set:

  cd apps/api && python scripts/seed_admin.py
"""

from __future__ import annotations

import argparse
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config import get_settings
from app.db.models import UserModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a login user for the orchestrator API.")
    parser.add_argument("--email", default=os.environ.get("SEED_ADMIN_EMAIL", "admin@demo.local"))
    parser.add_argument("--password", default=os.environ.get("SEED_ADMIN_PASSWORD", "ChangeMe123!"))
    parser.add_argument("--tenant", default=os.environ.get("APP_DEFAULT_TENANT", "demo-tenant"))
    parser.add_argument("--user-id", dest="user_id", default=os.environ.get("SEED_USER_ID", ""))
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    user_id = args.user_id or str(uuid.uuid4())
    now = datetime.now(UTC)
    pw_hash = hash_password(args.password)

    with Session(engine) as session:
        email_lower = args.email.strip().lower()
        existing = (
            session.query(UserModel)
            .filter(func.lower(UserModel.email) == email_lower)
            .one_or_none()
        )
        if existing:
            existing.hashed_password = pw_hash
            existing.roles = ["Admin", "Manager", "Employee"]
            existing.is_active = "active"
            existing.tenant_id = args.tenant
            existing.updated_at = now
            session.commit()
            print(f"Updated user {existing.user_id} ({existing.email}).")
            return

        row = UserModel(
            user_id=user_id,
            tenant_id=args.tenant,
            email=email_lower,
            hashed_password=pw_hash,
            roles=["Admin", "Manager", "Employee"],
            is_active="active",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        print(f"Created user {user_id} ({row.email}).")


if __name__ == "__main__":
    main()
