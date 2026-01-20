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
    TokenizeRequest,
    TokenizeResponse,
    TokenizerSelectRequest,
)
from app.services.tokenizer_admin_service import TokenizerAdminService
from app.tokenizer import get_tokenizer_manager

router = APIRouter()


def _normalize_scene_id(scene_id: object) -> int:
    """
    兼容两种调用方式：
    1) FastAPI 运行时：scene_id 为 int
    2) 单元测试/直接函数调用：scene_id 可能是 Query(...) 返回的参数对象
    """
    value = getattr(scene_id, "default", scene_id)
    return int(value)


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
        service.upsert_term(payload.term, payload.operation, scene_id=_normalize_scene_id(scene_id))
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
            scene_id=_normalize_scene_id(scene_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(
        data=BatchResultResponse(success_count=success_count, fail_count=fail_count)
    )


@router.post("/tokenize", response_model=ApiResponse[TokenizeResponse])
def tokenize_text(
    payload: TokenizeRequest,
    scene_id: int = Query(0, ge=0, description="场景ID（默认0）"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[TokenizeResponse]:
    """
    分词（调试接口）：返回当前场景下的分词结果（包含自定义词条覆盖层）。
    """
    manager = get_tokenizer_manager(db, scene_id=_normalize_scene_id(scene_id))
    text = (payload.text or "").strip()
    tokens = manager.tokenize(text) if text else []
    return ApiResponse(
        data=TokenizeResponse(tokenizerId=manager.current_tokenizer_id(), tokens=tokens)
    )
