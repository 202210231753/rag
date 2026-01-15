"""同义词挖掘 API。"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.stats_schema import ApiResponse
from app.services.synonym_mining import MiningJobScheduler, LocalEmbeddingMiner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run", response_model=ApiResponse)
def run_mining(
    domain: str = Query(default="default"),
    threshold: float = Query(default=0.82, ge=0.0, le=1.0),
    use_embedding: bool = Query(default=True, description="是否使用 Embedding 挖掘"),
    use_search_log: bool = Query(default=True, description="是否使用搜索日志挖掘"),
    search_log_days: int = Query(default=30, ge=1, le=365, description="搜索日志回溯天数"),
    search_log_min_clicks: int = Query(default=2, ge=1, description="搜索日志最小点击次数"),
    search_log_min_ratio: float = Query(default=0.3, ge=0.0, le=1.0, description="搜索日志最小共同点击比例"),
    db: Session = Depends(deps.get_db),
):
    """手动触发挖掘任务（支持多种挖掘策略）。"""
    try:
        strategy = LocalEmbeddingMiner() if use_embedding else None
        scheduler = MiningJobScheduler(db, strategy)
        count = scheduler.run_mining(
            domain=domain,
            threshold=threshold,
            use_embedding=use_embedding,
            use_search_log=use_search_log,
            search_log_days=search_log_days,
            search_log_min_clicks=search_log_min_clicks,
            search_log_min_ratio=search_log_min_ratio,
        )
        return ApiResponse(data={"count": count}, msg=f"挖掘完成，生成 {count} 个候选")
    except Exception as e:
        logger.error(f"挖掘任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

