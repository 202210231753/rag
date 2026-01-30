"""学术论文搜索 API 端点。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.paper_schema import PaperSearchRequest, PaperSearchResponse
from app.schemas.stats_schema import ApiResponse
from app.services.paper_search_service import paper_search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=ApiResponse[PaperSearchResponse])
def search_papers(request: PaperSearchRequest) -> ApiResponse[PaperSearchResponse]:
    """搜索学术论文。
    
    实际 URL: POST /api/v1/papers/search
    
    支持功能：
    - 按主题/关键词搜索论文
    - 按会议/期刊筛选
    - 按年份范围筛选
    - 优先返回顶会顶刊论文（CCS、USENIX Security、NDSS、IEEE S&P等）
    
    Args:
        request: 搜索请求，包含查询关键词、限制条件等
        
    Returns:
        包含论文列表的响应
        
    Examples:
        >>> # 搜索多智能体安全代码生成论文
        >>> POST /api/v1/papers/search
        >>> {
        >>>     "query": "multi-agent secure code generation",
        >>>     "limit": 5,
        >>>     "yearFrom": 2020
        >>> }
    """
    try:
        logger.info(f"搜索论文: query='{request.query}', limit={request.limit}")
        
        # 调用搜索服务
        result = paper_search_service.search_papers(request)
        
        logger.info(f"找到 {result.total} 篇论文")
        
        return ApiResponse(
            code=200,
            msg="搜索成功",
            data=result,
        )
        
    except Exception as e:
        logger.error(f"论文搜索失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"论文搜索失败: {str(e)}",
        )


@router.get("/health")
def health_check():
    """健康检查端点。"""
    return {
        "status": "healthy",
        "service": "paper_search",
        "features": [
            "semantic_scholar_integration",
            "top_venue_filtering",
            "citation_ranking",
        ],
    }
