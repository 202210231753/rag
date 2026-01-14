from __future__ import annotations

import os

from fastapi import Header, HTTPException


def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Lightweight admin guard.

    - If env var ADMIN_TOKEN is not set, all requests are allowed (dev-friendly).
    - If ADMIN_TOKEN is set, require either:
      - X-Admin-Token: <token>
      - Authorization: Bearer <token>
    """

    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        return

    provided = x_admin_token
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    if not provided or provided != expected:
        raise HTTPException(status_code=403, detail="Admin token required")
