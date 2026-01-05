from pydantic import BaseModel
from typing import List, Optional
from app.models.document import Visibility

class DocumentPermissionUpdate(BaseModel):
    visibility: Visibility
    authorized_group_ids: Optional[List[int]] = []

    class Config:
        from_attributes = True
