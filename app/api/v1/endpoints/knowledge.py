from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.document import Document
from app.services.rag_service import rag_service
from app.schemas.document_schema import DocumentPermissionUpdate

router = APIRouter()

class DocStatusUpdate(BaseModel):
    is_active: bool

@router.post("/{document_id}/status", summary="设置文档上下线状态")
async def set_document_status(
    document_id: int,
    status_update: DocStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    设置文档的上下线状态 (Online/Offline)。
    - **is_active=True**: 上线。文档内容会被重新向量化并加入检索库。
    - **is_active=False**: 下线。文档对应的向量数据会被物理删除，不再参与检索。
    """
    # 1. 检查文档是否存在
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 2. 检查状态是否真的需要变更
    if doc.is_active == status_update.is_active:
        return {"message": f"Document is already {'active' if doc.is_active else 'inactive'}", "id": document_id, "is_active": doc.is_active}

    # 3. 调用 Service 执行变更 (包含 Milvus 操作)
    try:
        rag_service.toggle_doc_status(document_id, status_update.is_active)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")
    
    return {
        "message": "Status updated successfully",
        "id": document_id,
        "is_active": status_update.is_active
    }

@router.put("/{document_id}/permission", summary="配置文档数据权限")
async def update_document_permission(
    document_id: int,
    permission_update: DocumentPermissionUpdate,
    db: Session = Depends(get_db)
):
    """
    配置文档的可见性权限。
    - **visibility**: private (仅自己), public (全员), group (指定组)
    - **authorized_group_ids**: 当 visibility=group 时，指定可见的组 ID 列表
    """
    # 1. 检查文档是否存在
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 2. 校验参数
    if permission_update.visibility == "group" and not permission_update.authorized_group_ids:
        raise HTTPException(status_code=400, detail="authorized_group_ids is required when visibility is 'group'")

    # 3. 调用 Service
    try:
        rag_service.update_doc_permission(
            document_id, 
            permission_update.visibility, 
            permission_update.authorized_group_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update permission: {str(e)}")
    
    return {
        "message": "Permission updated successfully",
        "id": document_id,
        "visibility": permission_update.visibility,
        "authorized_group_ids": permission_update.authorized_group_ids
    }

@router.get("/list", summary="获取文档列表")
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取文档列表，支持按状态过滤。
    """
    query = db.query(Document)
    
    if is_active is not None:
        query = query.filter(Document.is_active == is_active)
        
    total = query.count()
    docs = query.order_by(Document.id.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": docs
    }
