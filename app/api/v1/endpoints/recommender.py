"""
智能推荐模块的 API 端点
包含内容推荐和查询推荐两个核心功能
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from app.api import deps
from app.schemas.recommender_schema import (
    ContentRecommendRequest,
    ContentRecommendResponse,
    QueryRecommendRequest,
    QueryRecommendResponse,
    ErrorResponse,
    ExplanationItemResponse,
    ItemResponse
)
from app.services.recommender_service import ContentRecommenderService, QueryRecommenderService
from app.core.user_profile_manager import UserProfileManager
from app.core.ranking_engine import RankingEngine
from app.infra.config import ConfigCenter
from app.infra.ai_client import AIModelClient
from app.infra.vector_db import VectorDBClient
from app.data.models import ExplanationItem, Item

router = APIRouter()

# ============= 依赖注入：初始化服务 =============

def get_content_recommender_service() -> ContentRecommenderService:
    """
    创建内容推荐服务实例（依赖注入）
    在实际生产环境中，这些对象应该作为单例或者从容器中获取
    """
    # 初始化各个依赖组件
    config_center = ConfigCenter()
    ai_client = AIModelClient()
    vector_db = VectorDBClient()
    profile_manager = UserProfileManager()
    ranking_engine = RankingEngine()
    
    return ContentRecommenderService(
        profile_manager=profile_manager,
        ranking_engine=ranking_engine,
        config_center=config_center,
        ai_client=ai_client,
        vector_db=vector_db
    )


def get_query_recommender_service() -> QueryRecommenderService:
    """
    创建查询推荐服务实例（依赖注入）
    """
    config_center = ConfigCenter()
    ai_client = AIModelClient()
    vector_db = VectorDBClient()
    
    return QueryRecommenderService(
        config_center=config_center,
        ai_client=ai_client,
        vector_db=vector_db
    )


# ============= 辅助函数：数据转换 =============

def convert_to_item_response(item: Item) -> ItemResponse:
    """将内部 Item 模型转换为 API 响应模型"""
    return ItemResponse(
        item_id=item.item_id,
        content=item.content,
        tags=item.tags,
        score=item.score,
        strategy_source=item.strategy_source
    )


def convert_to_explanation_response(exp_item: ExplanationItem) -> ExplanationItemResponse:
    """将内部 ExplanationItem 模型转换为 API 响应模型"""
    return ExplanationItemResponse(
        item=convert_to_item_response(exp_item.item),
        explanation=exp_item.explanation
    )


# ============= API 端点 =============

@router.post("/content", 
             response_model=ContentRecommendResponse,
             summary="获取个性化内容推荐",
             description="基于用户画像和兴趣标签，返回个性化推荐内容列表（带推荐理由）")
async def recommend_content(
    request: ContentRecommendRequest,
    service: ContentRecommenderService = Depends(get_content_recommender_service)
):
    """
    **内容推荐接口**
    
    - **user_id**: 用户唯一标识
    - **trace_id**: 可选的追踪ID，用于日志关联和问题排查
    
    返回个性化推荐的内容列表，每个内容包含推荐理由。
    推荐算法综合考虑：
    - 用户静态标签和动态兴趣
    - 地理位置和负面过滤
    - 热搜提升和多样性平衡
    """
    try:
        # 生成 trace_id（如果没有提供）
        trace_id = request.trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        
        # 调用推荐服务
        results: List[ExplanationItem] = service.recommend(
            user_id=request.user_id,
            trace_id=trace_id
        )
        
        # 转换为响应格式
        recommendations = [convert_to_explanation_response(item) for item in results]
        
        return ContentRecommendResponse(
            success=True,
            user_id=request.user_id,
            trace_id=trace_id,
            recommendations=recommendations,
            count=len(recommendations),
            timestamp=datetime.now()
        )
        
    except ValueError as e:
        # 业务逻辑错误（如用户不存在）
        raise HTTPException(
            status_code=404,
            detail={"error_code": "USER_NOT_FOUND", "error_message": str(e)}
        )
    except Exception as e:
        # 系统错误
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": f"推荐服务异常: {str(e)}"
            }
        )


@router.post("/query",
             response_model=QueryRecommendResponse,
             summary="获取相关查询推荐",
             description="根据当前查询词，推荐相关的搜索词（算法 + 热搜 + 精选）")
async def recommend_queries(
    request: QueryRecommendRequest,
    service: QueryRecommenderService = Depends(get_query_recommender_service)
):
    """
    **查询推荐接口**
    
    - **current_query**: 当前用户输入的查询词
    - **trace_id**: 可选的追踪ID，用于日志关联和问题排查
    
    返回相关的搜索词建议列表（最多5个）。
    推荐策略：
    - 槽位0: 精选内容（如果有配置）
    - 槽位1: 算法相似查询
    - 槽位2: 热门搜索
    - 槽位3+: 混合填充
    """
    try:
        # 生成 trace_id（如果没有提供）
        trace_id = request.trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        
        # 调用推荐服务
        recommended_queries: List[str] = service.recommend_next_queries(
            current_query=request.current_query,
            trace_id=trace_id
        )
        
        return QueryRecommendResponse(
            success=True,
            current_query=request.current_query,
            trace_id=trace_id,
            recommended_queries=recommended_queries,
            count=len(recommended_queries),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        # 系统错误
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": f"查询推荐服务异常: {str(e)}"
            }
        )


@router.get("/health",
            summary="推荐服务健康检查",
            description="检查推荐服务及其依赖是否正常运行")
async def health_check():
    """
    **健康检查接口**
    
    用于监控推荐服务的运行状态
    """
    return {
        "status": "healthy",
        "service": "recommender",
        "timestamp": datetime.now(),
        "endpoints": {
            "content_recommend": "/api/v1/recommender/content",
            "query_recommend": "/api/v1/recommender/query"
        }
    }

