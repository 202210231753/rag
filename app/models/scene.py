from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Scene(Base):
    """
    场景配置主表
    用于隔离不同业务线（如：财务助手、HR问答、通用客服）
    """
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scene_name = Column(String(50), nullable=False, comment="场景名称，如：财务助手")
    scene_tag = Column(String(50), unique=True, index=True, nullable=False, comment="场景标识，API调用时使用，如：finance_bot")
    description = Column(String(200), comment="场景描述")
    department = Column(String(50), comment="所属部门，用于权限隔离")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联策略配置 (级联删除)
    strategies = relationship("SceneStrategy", back_populates="scene", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scene(tag='{self.scene_tag}', name='{self.scene_name}')>"


class SceneStrategy(Base):
    """
    场景策略映射表
    存储具体的管控配置，如：召回范围、排序模型、敏感词库绑定等
    """
    __tablename__ = "scene_strategies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    
    # 策略类型枚举建议: 
    # - recall: 召回策略 (top_k, 阈值)
    # - ranking: 排序策略 (模型选择)
    # - data_scope: 数据范围 (绑定特定的知识库ID或标签)
    # - sensitive: 敏感词/干预 (白名单ID, 敏感词组ID)
    # - prompt: 提示词模板
    strategy_type = Column(String(50), nullable=False, comment="策略类型") 
    
    # 策略具体配置，使用 JSON 存储灵活性高的配置
    # 例如: {"model": "bge-rerank-large", "weights": 0.8}
    strategy_value = Column(JSON, nullable=False, comment="策略配置值")
    
    priority = Column(Integer, default=0, comment="优先级，数字越大优先级越高")
    
    scene = relationship("Scene", back_populates="strategies")

    # 同一个场景下，同一种策略类型通常只需要一条（或者多条按优先级）
    # 这里我们暂不加唯一约束，允许复杂场景
