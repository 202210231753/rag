"""检索 API（集成同义词）。"""
from __future__ import annotations

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.stats_schema import ApiResponse
from app.services.search_service import SearchService
from app.models.stats import SearchLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=ApiResponse)
def search(
    query: str = Query(..., description="查询文本"),
    domain: str = Query(default="default", description="领域"),
    index: str = Query(default="documents", description="ES 索引名"),
    field: str = Query(default="content", description="查询字段"),
    size: int = Query(default=10, ge=1, le=100, description="返回结果数量"),
    debug: bool = Query(default=False, description="是否返回改写计划"),
    user_id: int = Query(default=None, description="用户ID（用于记录搜索日志）"),
    log_click: bool = Query(default=False, description="是否记录搜索日志"),
    db: Session = Depends(deps.get_db),
):
    """检索接口（带同义词扩展）。"""
    try:
        service = SearchService(db)
        result = service.search(
            query=query,
            domain=domain,
            index=index,
            field=field,
            size=size,
            return_rewrite_plan=debug,
        )
        
        # 记录搜索日志（如果启用）
        if log_click and user_id:
            try:
                search_log = SearchLog(
                    user_id=user_id,
                    timestamp=datetime.now(),
                    query=query,
                )
                db.add(search_log)
                db.commit()
            except Exception as e:
                logger.warning(f"记录搜索日志失败: {e}", exc_info=logger.isEnabledFor(logging.DEBUG))
        
        return ApiResponse(data=result, msg="检索成功")
    except Exception as e:
        logger.error(f"检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/click")
def log_search_click(
    query: str = Query(..., description="搜索查询词"),
    doc_id: str = Query(..., description="点击的文档ID"),
    doc_title: str = Query(default=None, description="点击的文档标题"),
    user_id: int = Query(default=None, description="用户ID"),
    db: Session = Depends(deps.get_db),
):
    """记录搜索点击日志（用于同义词挖掘）。"""
    try:
        search_log = SearchLog(
            user_id=user_id or 0,  # 如果没有 user_id，使用 0
            timestamp=datetime.now(),
            query=query,
            clicked_doc_id=doc_id,
            clicked_doc_title=doc_title,
        )
        db.add(search_log)
        db.commit()
        return ApiResponse(data={"logged": True}, msg="点击日志记录成功")
    except Exception as e:
        logger.error(f"记录点击日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

