"""
搜索 API 端点

多路召回搜索接口
"""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.schemas.search_schema import SearchRequest
from app.rag.models.search_result import SearchResult
from app.rag.search_gateway import SearchGateway
from app.api.deps import get_search_gateway  # 从 deps 导入
from app.api.deps import get_hot_search_service
from app.hot_search.service import HotSearchService

router = APIRouter()


@router.post("/multi-recall", response_model=SearchResult, tags=["搜索"])
async def multi_recall_search(
    request: SearchRequest,
    gateway: SearchGateway = Depends(get_search_gateway),
    hot_search: HotSearchService = Depends(get_hot_search_service),
):
    """
    多路召回搜索

    执行向量召回 + 关键词召回，使用 RRF 融合，可选重排

    **流程：**
    1. 向量化查询（OpenAI Embedding）
    2. 分词查询（jieba）
    3. 并行召回：
       - 向量召回（Milvus）
       - 关键词召回（ElasticSearch BM25）
    4. RRF 融合（1/(60+rank)）
    5. 可选重排（暂未实现）

    **参数说明：**
    - `query`: 用户查询字符串
    - `top_n`: 返回结果数量（默认10）
    - `recall_top_k`: 每路召回的TopK（默认100）
    - `enable_rerank`: 是否启用重排（默认False，暂不支持）
    """
    try:
        logger.info(f"[API] 收到搜索请求: query='{request.query}', top_n={request.top_n}")

        # 调用 SearchGateway 执行搜索（成功返回即视为“检索成功”）
        result = await gateway.search(
            query=request.query,
            top_n=request.top_n,
            recall_top_k=request.recall_top_k,
            enable_rerank=request.enable_rerank,
            enable_ranking=request.enable_ranking,
        )

        # 热搜计数：仅在检索成功(HTTP 200)后记录；即便 total=0 也计数
        try:
            await hot_search.record_search_action(request.query)
        except Exception as exc:
            logger.warning(f"[HotSearch] 记录热度失败（不影响搜索返回）: {exc}")

        logger.info(
            f"[API] 搜索成功: results={result.total}, took={result.took_ms:.2f}ms"
        )
        return result

    except Exception as e:
        logger.error(f"[API] 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查端点

    用于检查搜索服务是否正常运行
    """
    return {"status": "healthy", "service": "multi-recall-search"}
