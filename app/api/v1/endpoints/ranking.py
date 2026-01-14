"""
排序引擎管理 API

提供 lambda 参数配置、黑名单管理、位置插入规则管理接口。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.redis_client import RedisClient, get_redis_client
from loguru import logger

router = APIRouter()


# ========================================
# Pydantic 模型
# ========================================
class LambdaConfigUpdate(BaseModel):
    """Lambda 参数更新请求"""

    lambda_param: float = Field(..., ge=0, le=1, description="MMR 平衡参数 (0-1)")


class LambdaConfigResponse(BaseModel):
    """Lambda 参数响应"""

    lambda_param: float
    updated_at: str


class BlacklistRequest(BaseModel):
    """黑名单操作请求"""

    action: str = Field(..., description="操作类型: add/remove")
    doc_ids: List[str] = Field(..., description="文档ID列表")


class BlacklistResponse(BaseModel):
    """黑名单操作响应"""

    action: str
    affected_count: int
    total_count: int


class PositionRuleRequest(BaseModel):
    """位置插入规则请求"""

    query: str = Field(..., description="查询关键词")
    doc_id: str = Field(..., description="文档ID")
    position: int = Field(..., ge=0, description="目标位置 (0-based)")


class PositionRuleResponse(BaseModel):
    """位置规则响应"""

    query: str
    doc_id: str
    position: int


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str
    success: bool = True


# ========================================
# Lambda 参数管理
# ========================================
@router.get("/lambda", response_model=LambdaConfigResponse, summary="获取 Lambda 参数")
async def get_lambda_config(db: Session = Depends(get_db)):
    """获取当前的 MMR Lambda 参数配置"""
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT lambda_param, updated_at FROM diversity_config WHERE id = 1")).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="配置不存在")

        return LambdaConfigResponse(lambda_param=result[0], updated_at=str(result[1]))

    except Exception as e:
        logger.error(f"获取 lambda 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/lambda", response_model=LambdaConfigResponse, summary="更新 Lambda 参数")
async def update_lambda_config(
    config: LambdaConfigUpdate, db: Session = Depends(get_db)
):
    """
    更新 MMR Lambda 参数
    
    - lambda=0: 只看多样性（不考虑相关性）
    - lambda=1: 只看相关性（不考虑多样性）
    - lambda=0.5: 平衡相关性和多样性
    """
    try:
        from sqlalchemy import text
        db.execute(
            text("UPDATE diversity_config SET lambda_param = :lambda WHERE id = 1"),
            {"lambda": config.lambda_param},
        )
        db.commit()

        result = db.execute(text("SELECT lambda_param, updated_at FROM diversity_config WHERE id = 1")).fetchone()

        logger.info(f"✅ Lambda 参数已更新: {config.lambda_param}")
        return LambdaConfigResponse(lambda_param=result[0], updated_at=str(result[1]))

    except Exception as e:
        db.rollback()
        logger.error(f"更新 lambda 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 黑名单管理
# ========================================
@router.post("/blacklist", response_model=BlacklistResponse, summary="黑名单操作")
async def manage_blacklist(
    request: BlacklistRequest, redis: RedisClient = Depends(get_redis_client)
):
    """
    添加或移除黑名单文档
    
    - action: "add" 添加到黑名单
    - action: "remove" 从黑名单移除
    """
    try:
        if request.action == "add":
            affected = await redis.add_to_blacklist(request.doc_ids)
            logger.info(f"✅ 黑名单添加: {affected} 条")
        elif request.action == "remove":
            affected = await redis.remove_from_blacklist(request.doc_ids)
            logger.info(f"✅ 黑名单移除: {affected} 条")
        else:
            raise HTTPException(status_code=400, detail="action 必须是 'add' 或 'remove'")

        # 获取当前黑名单总数
        total = len(await redis.get_blacklist())

        return BlacklistResponse(
            action=request.action, affected_count=affected, total_count=total
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"黑名单操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blacklist", response_model=List[str], summary="获取黑名单列表")
async def get_blacklist(redis: RedisClient = Depends(get_redis_client)):
    """获取所有黑名单文档ID"""
    try:
        blacklist = await redis.get_blacklist()
        return sorted(list(blacklist))
    except Exception as e:
        logger.error(f"获取黑名单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 位置插入规则管理
# ========================================
@router.post("/position", response_model=PositionRuleResponse, summary="设置位置插入规则")
async def set_position_rule(
    request: PositionRuleRequest, redis: RedisClient = Depends(get_redis_client)
):
    """
    设置位置插入规则
    
    指定查询匹配时，将某个文档强制插入到指定位置（置顶/置底等）
    """
    try:
        await redis.set_position_rule(request.query, request.doc_id, request.position)

        return PositionRuleResponse(
            query=request.query, doc_id=request.doc_id, position=request.position
        )

    except Exception as e:
        logger.error(f"设置位置规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position", response_model=dict, summary="获取所有位置规则")
async def get_all_position_rules(redis: RedisClient = Depends(get_redis_client)):
    """
    获取所有位置插入规则
    
    返回格式: {"query1": {"doc_id": "xxx", "position": 0}, ...}
    """
    try:
        rules = await redis.get_all_position_rules()
        # 转换格式
        result = {}
        for query, (doc_id, position) in rules.items():
            result[query] = {"doc_id": doc_id, "position": position}

        return result

    except Exception as e:
        logger.error(f"获取位置规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/position/{query}", response_model=MessageResponse, summary="删除位置规则")
async def delete_position_rule(query: str, redis: RedisClient = Depends(get_redis_client)):
    """删除指定查询的位置插入规则"""
    try:
        success = await redis.delete_position_rule(query)

        if success:
            logger.info(f"✅ 位置规则已删除: query='{query}'")
            return MessageResponse(message=f"规则 '{query}' 已删除", success=True)
        else:
            raise HTTPException(status_code=404, detail=f"规则 '{query}' 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除位置规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
