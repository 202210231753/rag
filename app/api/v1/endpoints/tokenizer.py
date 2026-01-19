from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.tokenizer.manager import Operation
from app.api import deps
from app.schemas.stats_schema import ApiResponse
from app.schemas.tokenizer_schema import (
    BatchResultResponse,
    SuccessResponse,
    TermUpsertRequest,
    TokenizerSelectRequest,
)
from app.services.tokenizer_admin_service import TokenizerAdminService

router = APIRouter()


@router.post("/select", response_model=ApiResponse[SuccessResponse])
def select_tokenizer(
    payload: TokenizerSelectRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[SuccessResponse]:
    """
    分词器选择：根据 tokenizerId 切换系统当前使用的分词器。
    """
    service = TokenizerAdminService(db)
    try:
        service.select_tokenizer(payload.tokenizer_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=SuccessResponse(success=True))


@router.post("/term", response_model=ApiResponse[SuccessResponse])
def upsert_term(
    payload: TermUpsertRequest,
    scene_id: int = Query(0, ge=0, description="场景ID（默认0）"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[SuccessResponse]:
    """
    专用词条增删：对单个词条执行 ADD/DELETE。
    """
    service = TokenizerAdminService(db)
    try:
        service.upsert_term(payload.term, payload.operation, scene_id=scene_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=SuccessResponse(success=True))


@router.post("/terms/batch", response_model=ApiResponse[BatchResultResponse])
async def batch_upsert_terms(
    file: UploadFile = File(..., description="包含词条列表的文本文件（UTF-8）"),
    operation: str = Form(..., description="批量操作类型：ADD(新增), DELETE(删除)"),
    scene_id: int = Query(0, ge=0, description="场景ID（默认0）"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[BatchResultResponse]:
    """
    专用词条批量增删：上传文件批量处理词条。
    """
    service = TokenizerAdminService(db)
    op = operation.strip().upper()
    if op not in {"ADD", "DELETE"}:
        raise HTTPException(status_code=400, detail="operation 仅支持 ADD/DELETE")
    try:
        success_count, fail_count = await service.batch_upsert_terms(
            upload_file=file,
            operation=cast(Operation, op),
            scene_id=scene_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(
        data=BatchResultResponse(success_count=success_count, fail_count=fail_count)
    )

