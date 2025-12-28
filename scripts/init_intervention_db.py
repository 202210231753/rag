"""Create intervention-related tables in MySQL.

Usage:
  1) Ensure .env is configured for DB connection.
  2) Run: python scripts/init_intervention_db.py

This script only creates tables if they don't exist.
"""

from __future__ import annotations

from app.core.database import engine
from app.intervention import models as _models  # noqa: F401
from app.core.database import Base


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ Intervention tables ensured (create_all executed).")


if __name__ == "__main__":
    main()
