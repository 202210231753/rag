from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# =======================
# Strategy Schemas
# =======================
class SceneStrategyBase(BaseModel):
    strategy_type: str = Field(..., description="策略类型，如: recall, ranking, sensitive")
    strategy_value: Dict[str, Any] = Field(..., description="具体的JSON配置")
    priority: int = Field(0, description="优先级")

class SceneStrategyCreate(SceneStrategyBase):
    pass

class SceneStrategyUpdate(BaseModel):
    strategy_type: Optional[str] = None
    strategy_value: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None

class SceneStrategyOut(SceneStrategyBase):
    id: int
    scene_id: int

    class Config:
        orm_mode = True


# =======================
# Scene Schemas
# =======================
class SceneBase(BaseModel):
    scene_name: str = Field(..., min_length=2, max_length=50, description="场景显示名称")
    scene_tag: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$", description="场景唯一标识，只能包含字母数字下划线")
    description: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True

class SceneCreate(SceneBase):
    strategies: List[SceneStrategyCreate] = []

class SceneUpdate(BaseModel):
    scene_name: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    # strategies 的更新通常建议走单独的接口，或者全量覆盖，这里暂不包含在简单 update 中

class SceneOut(SceneBase):
    id: int
    created_at: datetime
    updated_at: datetime
    strategies: List[SceneStrategyOut] = []

    class Config:
        orm_mode = True
