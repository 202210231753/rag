from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
import logging

from app.models.scene import Scene, SceneStrategy
from app.schemas.scene import SceneCreate, SceneUpdate, SceneStrategyCreate

logger = logging.getLogger(__name__)

class SceneService:
    def create_scene(self, db: Session, scene_in: SceneCreate) -> Scene:
        """创建新场景，包含其策略配置"""
        # 1. Check if tag exists
        existing = db.query(Scene).filter(Scene.scene_tag == scene_in.scene_tag).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scene tag '{scene_in.scene_tag}' already exists."
            )

        # 2. Create Scene
        db_scene = Scene(
            scene_name=scene_in.scene_name,
            scene_tag=scene_in.scene_tag,
            description=scene_in.description,
            department=scene_in.department,
            is_active=scene_in.is_active
        )
        db.add(db_scene)
        
        try:
            db.flush() # flush to get ID
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error.")

        # 3. Create Strategies
        if scene_in.strategies:
            for strat in scene_in.strategies:
                db_strat = SceneStrategy(
                    scene_id=db_scene.id,
                    strategy_type=strat.strategy_type,
                    strategy_value=strat.strategy_value,
                    priority=strat.priority
                )
                db.add(db_strat)
        
        db.commit()
        db.refresh(db_scene)
        return db_scene

    def get_scene_by_tag(self, db: Session, scene_tag: str) -> Optional[Scene]:
        return db.query(Scene).filter(Scene.scene_tag == scene_tag).first()

    def get_scenes(self, db: Session, skip: int = 0, limit: int = 100) -> List[Scene]:
        return db.query(Scene).offset(skip).limit(limit).all()

    def update_scene(self, db: Session, scene_tag: str, scene_in: SceneUpdate) -> Scene:
        db_scene = self.get_scene_by_tag(db, scene_tag)
        if not db_scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        
        update_data = scene_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_scene, field, value)
            
        db.commit()
        db.refresh(db_scene)
        return db_scene

    def delete_scene(self, db: Session, scene_tag: str):
        db_scene = self.get_scene_by_tag(db, scene_tag)
        if not db_scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        
        db.delete(db_scene)
        db.commit()

    # ==========================
    # 策略管理相关方法
    # ==========================
    def add_strategy(self, db: Session, scene_tag: str, strategy: SceneStrategyCreate):
        db_scene = self.get_scene_by_tag(db, scene_tag)
        if not db_scene:
            raise HTTPException(status_code=404, detail="Scene not found")
            
        db_strat = SceneStrategy(
            scene_id=db_scene.id,
            strategy_type=strategy.strategy_type,
            strategy_value=strategy.strategy_value,
            priority=strategy.priority
        )
        db.add(db_strat)
        db.commit()
        db.refresh(db_scene)
        return db_scene

    def get_full_config(self, db: Session, scene_tag: str) -> Dict[str, Any]:
        """
        [RAG 核心方法]
        获取聚合后的场景配置字典，供 RAG 流程直接使用。
        后续应封装 Redis 缓存。
        """
        scene = db.query(Scene).filter(Scene.scene_tag == scene_tag, Scene.is_active == True).first()
        if not scene:
            logger.warning(f"[SceneService] Scene '{scene_tag}' not found or inactive.")
            return {}

        config_map = {
            "scene_name": scene.scene_name,
            "department": scene.department,
            "strategies": {}
        }

        # 聚合策略：按类型分组
        # 注意：如果同一个类型有多个策略，这里简单的逻辑是：
        # 如果是列表结构(如敏感词库)则合并; 如果是单一配置(如模型)则取高优先级;
        # 这里简化处理：直接按类型存入 list，由业务层消费决定
        strategies_grouped = {}
        # 按 priority 倒序遍历（优先级高的在前）
        sorted_strats = sorted(scene.strategies, key=lambda x: x.priority, reverse=True)
        
        for s in sorted_strats:
            if s.strategy_type not in strategies_grouped:
                strategies_grouped[s.strategy_type] = []
            strategies_grouped[s.strategy_type].append(s.strategy_value)
            
        config_map["strategies"] = strategies_grouped
        return config_map

scene_service = SceneService()
