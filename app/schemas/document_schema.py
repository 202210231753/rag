from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.models.document import Visibility


class DocumentPermissionUpdate(BaseModel):
    visibility: Visibility
    authorized_group_ids: Optional[List[int]] = None

