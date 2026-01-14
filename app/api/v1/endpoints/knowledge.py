from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.document import Document
from app.services.rag_service import rag_service

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
