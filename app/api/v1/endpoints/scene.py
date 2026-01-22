from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.scene import SceneCreate, SceneOut, SceneUpdate, SceneStrategyCreate
from app.services.scene_service import scene_service

router = APIRouter()

@router.post("/", response_model=SceneOut, summary="创建新场景")
def create_new_scene(
    scene_in: SceneCreate, 
    db: Session = Depends(get_db)
):
    """
    创建一个新的业务场景，并可以同时配置初始化策略。
    """
    return scene_service.create_scene(db, scene_in)

@router.get("/", response_model=List[SceneOut], summary="获取场景列表")
def list_scenes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    return scene_service.get_scenes(db, skip=skip, limit=limit)

@router.get("/{scene_tag}", response_model=SceneOut, summary="获取场景详情")
def get_scene_details(
    scene_tag: str, 
    db: Session = Depends(get_db)
):
    scene = scene_service.get_scene_by_tag(db, scene_tag)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene

@router.put("/{scene_tag}", response_model=SceneOut, summary="更新场景基础信息")
def update_scene_info(
    scene_tag: str, 
    scene_in: SceneUpdate, 
    db: Session = Depends(get_db)
):
    return scene_service.update_scene(db, scene_tag, scene_in)

@router.delete("/{scene_tag}", summary="删除场景")
def delete_scene(
    scene_tag: str, 
    db: Session = Depends(get_db)
):
    scene_service.delete_scene(db, scene_tag)
    return {"message": f"Scene {scene_tag} deleted successfully"}

@router.post("/{scene_tag}/strategies", response_model=SceneOut, summary="添加策略")
def add_strategy_to_scene(
    scene_tag: str,
    strategy: SceneStrategyCreate,
    db: Session = Depends(get_db)
):
    """
    往现有场景中追加一条策略。
    """
    return scene_service.add_strategy(db, scene_tag, strategy)

@router.get("/{scene_tag}/effective-config", summary="查看生效配置(调试用)")
def get_effective_config(
    scene_tag: str,
    db: Session = Depends(get_db)
):
    """
    模拟 RAG 获取到的最终配置结构。
    """
    return scene_service.get_full_config(db, scene_tag)
