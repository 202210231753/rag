"""Create user-related tables in MySQL.

Usage:
  1) Ensure .env is configured for DB connection.
  2) Run: python "scripts/init_user_db.py"
"""

from __future__ import annotations

from app.core.database import Base, engine
from app.models import stats as _stats
from app.models import user as _user


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ User tables ensured (create_all executed).")


if __name__ == "__main__":
    main()
