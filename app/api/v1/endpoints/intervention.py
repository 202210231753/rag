from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.models.document import Document
from app.models.chunk import Chunk
from app.services.intervention_service import InterventionService

router = APIRouter()

# --- Pydantic Schemas (请求/响应模型) ---
# 为了简单起见，暂时写在这里。正规做法是放到 app/schemas/ 目录下
class ChunkUpdate(BaseModel):
    content: str

class ChunkStatusUpdate(BaseModel):
    is_active: bool

class ChunkResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    image_urls: Optional[List[str]] = None
    data_type: Optional[str] = "text"
    error_words: Optional[str] = None
    correct_words: Optional[str] = None
    owner_user_id: Optional[int] = None
    is_active: bool
    index: int
    vector_id: Optional[int] = None

    class Config:
        from_attributes = True # 兼容 ORM 对象

class DocumentResponse(BaseModel):
    id: int
    filename: str
    status: str
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(deps.get_db)
):
    """获取文档列表 (管理视角)"""
    docs = db.query(Document).offset(skip).limit(limit).all()
    # 简单的格式化，实际项目中可以用 Pydantic 自动转换
    return [
        DocumentResponse(
            id=d.id, 
            filename=d.filename, 
            status=d.status, 
            chunk_count=d.chunk_count,
            created_at=str(d.created_at)
        ) for d in docs
    ]

@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int, 
    db: Session = Depends(deps.get_db)
):
    """删除文档 (级联删除 MySQL + Milvus)"""
    service = InterventionService(db)
    success = service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

@router.get("/documents/{doc_id}/chunks", response_model=List[ChunkResponse])
def list_document_chunks(
    doc_id: int, 
    db: Session = Depends(deps.get_db)
):
    """获取某文档的所有切片"""
    chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.index).all()
    return chunks

@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
def update_chunk_content(
    chunk_id: int, 
    payload: ChunkUpdate, 
    db: Session = Depends(deps.get_db)
):
    """干预：修改切片内容并重算向量"""
    service = InterventionService(db)
    try:
        updated_chunk = service.update_chunk_content(chunk_id, payload.content)
        return updated_chunk
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intervention failed: {str(e)}")

@router.patch("/chunks/{chunk_id}/status", response_model=ChunkResponse)
def toggle_chunk_status(
    chunk_id: int, 
    payload: ChunkStatusUpdate, 
    db: Session = Depends(deps.get_db)
):
    """干预：启停切片"""
    service = InterventionService(db)
    try:
        updated_chunk = service.toggle_chunk_status(chunk_id, payload.is_active)
        return updated_chunk
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
