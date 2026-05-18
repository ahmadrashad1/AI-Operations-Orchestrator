"""Database migration utilities."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    """Run pending database migrations."""
    alembic_cfg = Config("alembic.ini")
    # Set the connection URL
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        os.getenv("APP_DATABASE_URL", "postgresql+psycopg://orchestrator:orchestrator@localhost:5432/orchestrator"),
    )
    # script_location comes from alembic.ini (Dockerfile rewrites it to `migrations/` to avoid shadowing the alembic package).

    # Run upgrade to latest migration
    command.upgrade(alembic_cfg, "head")


def downgrade_migrations(engine: Engine, revision: str = "-1") -> None:
    """Downgrade database migrations."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        os.getenv("APP_DATABASE_URL", "postgresql+psycopg://orchestrator:orchestrator@localhost:5432/orchestrator"),
    )

    command.downgrade(alembic_cfg, revision)
