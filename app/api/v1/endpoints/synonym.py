"""同义词管理 API 端点。"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.stats_schema import ApiResponse
from app.schemas.synonym_schema import (
    ManualUpsertRequest,
    BatchImportRequest,
    DeleteGroupsRequest,
    CandidateListResponse,
    ApproveRejectRequest,
    RewriteRequest,
    RewritePlan,
    SynonymCandidateSchema,
)
from app.services.synonym_service import SynonymService, ReviewService

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 公共工具函数 ==========


def handle_api_error(func: Callable) -> Callable:
    """API端点错误处理装饰器。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper


# ========== 同义词库管理 ==========


@router.get("/groups", response_model=ApiResponse)
@handle_api_error
def list_groups(
    domain: str = Query(default="default", description="领域"),
    limit: int = Query(default=100, ge=1, le=1000, description="每页数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(deps.get_db),
):
    """查询已存储的同义词组列表。"""
    service = SynonymService(db)
    groups, total = service.list_groups(domain, limit, offset)
    return ApiResponse(
        data={"groups": groups, "total": total},
        msg=f"查询成功，共 {total} 组"
    )


@router.post("/manual_upsert", response_model=ApiResponse)
@handle_api_error
def manual_upsert(
    request: ManualUpsertRequest,
    db: Session = Depends(deps.get_db),
):
    """手动添加同义词。"""
    service = SynonymService(db)
    group = service.manual_upsert(request.domain, request.canonical, request.synonyms)
    return ApiResponse(data=group, msg="添加成功")


@router.post("/batch_import", response_model=ApiResponse)
@handle_api_error
def batch_import(
    request: BatchImportRequest,
    db: Session = Depends(deps.get_db),
):
    """批量导入同义词（JSON 格式）。"""
    service = SynonymService(db)
    count = service.batch_import(request.domain, request.groups)
    return ApiResponse(data={"count": count}, msg=f"导入成功，共 {count} 组")


@router.post("/batch_import_file")
@handle_api_error
async def batch_import_file(
    file: UploadFile = File(...),
    domain: str = Query(default="default"),
    db: Session = Depends(deps.get_db),
):
    """批量导入同义词（上传文件：CSV/XLSX/JSON）。"""
    import json
    import csv
    from io import StringIO

    content = await file.read()
    file_ext = file.filename.split(".")[-1].lower()

    groups = []
    if file_ext == "json":
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            groups = data
        elif isinstance(data, dict) and "groups" in data:
            groups = data["groups"]
    elif file_ext == "csv":
        # CSV 格式：canonical,synonym1,synonym2,...
        text = content.decode("utf-8")
        reader = csv.DictReader(StringIO(text))
        groups_map = {}
        for row in reader:
            canonical = row.get("canonical", "").strip()
            if not canonical:
                continue
            if canonical not in groups_map:
                groups_map[canonical] = []
            # 读取所有同义词列
            for key, value in row.items():
                if key != "canonical" and value.strip():
                    groups_map[canonical].append(value.strip())
        groups = [{"canonical": k, "synonyms": v} for k, v in groups_map.items()]
    else:
        raise HTTPException(status_code=400, detail="不支持的文件格式，请使用 JSON 或 CSV")

    service = SynonymService(db)
    count = service.batch_import(domain, groups)
    return ApiResponse(data={"count": count}, msg=f"导入成功，共 {count} 组")


@router.delete("/groups", response_model=ApiResponse)
@handle_api_error
def delete_groups(
    request: DeleteGroupsRequest,
    db: Session = Depends(deps.get_db),
):
    """删除同义词组。"""
    service = SynonymService(db)
    count = service.remove_groups(request.group_ids)
    return ApiResponse(data={"count": count}, msg=f"删除成功，共 {count} 组")


# ========== 候选审核 ==========


@router.get("/candidates", response_model=ApiResponse[CandidateListResponse])
@handle_api_error
def list_candidates(
    domain: str = Query(default="default"),
    status: str = Query(default="pending"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(deps.get_db),
):
    """列出候选。"""
    if status not in ["pending", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="status 必须是 pending/approved/rejected")

    review_service = ReviewService(db)
    candidates, total = review_service.list_candidates(domain, status, limit, offset)

    candidate_schemas = [
        SynonymCandidateSchema(
            candidate_id=c.candidate_id,
            domain=c.domain,
            canonical=c.canonical,
            synonym=c.synonym,
            score=c.score,
            status=c.status,
            source=c.source,
            created_at=c.created_at,
        )
        for c in candidates
    ]

    return ApiResponse(
        data=CandidateListResponse(candidates=candidate_schemas, total=total),
        msg="查询成功",
    )


@router.post("/candidates/approve", response_model=ApiResponse)
@handle_api_error
def approve_candidates(
    request: ApproveRejectRequest,
    db: Session = Depends(deps.get_db),
):
    """审核通过候选。"""
    service = ReviewService(db)
    count = service.approve(request.ids)
    return ApiResponse(data={"count": count}, msg=f"审核通过 {count} 个候选")


@router.post("/candidates/reject", response_model=ApiResponse)
@handle_api_error
def reject_candidates(
    request: ApproveRejectRequest,
    db: Session = Depends(deps.get_db),
):
    """拒绝候选。"""
    service = ReviewService(db)
    count = service.reject(request.ids)
    return ApiResponse(data={"count": count}, msg=f"拒绝 {count} 个候选")


# ========== 查询改写 ==========


@router.post("/rewrite", response_model=ApiResponse[RewritePlan])
@handle_api_error
def rewrite_query(
    request: RewriteRequest,
    db: Session = Depends(deps.get_db),
):
    """查询改写（调试用）。"""
    service = SynonymService(db)
    plan = service.rewrite(request.domain, request.query)
    return ApiResponse(data=plan, msg="改写成功")

