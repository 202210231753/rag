from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.stats_schema import ApiResponse
from app.schemas.term_weight_schema import TermWeightSetRequest
from app.schemas.tokenizer_schema import SuccessResponse
from app.services.term_weight_service import TermWeightService

router = APIRouter()


def _normalize_scene_id(scene_id: object) -> int:
    """
    兼容两种调用方式：
    1) FastAPI 运行时：scene_id 为 int
    2) 单元测试/直接函数调用：scene_id 可能是 Query(...) 返回的参数对象
    """
    value = getattr(scene_id, "default", scene_id)
    return int(value)


@router.post("", response_model=ApiResponse[SuccessResponse])
def set_term_weight(
    payload: TermWeightSetRequest,
    scene_id: int = Query(0, ge=0, description="场景ID（默认0）"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[SuccessResponse]:
    """
    人工配置词权重：手动指定特定词条的权重值，用于干预排序。
    """
    service = TermWeightService(db, scene_id=_normalize_scene_id(scene_id))
    try:
        service.set_manual_weight(payload.term, payload.weight)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=SuccessResponse(success=True))


@router.post("/auto", response_model=ApiResponse[SuccessResponse])
def auto_calc_term_weights(
    scene_id: int = Query(0, ge=0, description="场景ID（默认0）"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[SuccessResponse]:
    """
    自动计算词权重：基于语料库按 IDF 重新计算词条权重（保留人工权重）。
    """
    service = TermWeightService(db, scene_id=_normalize_scene_id(scene_id))
    try:
        service.auto_recalculate_idf_weights()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=SuccessResponse(success=True))
