"""基础 Model 类，统一继承自数据库 Base。"""

from app.core.database import Base  # re-export for models to import统一来源

__all__ = ["Base"]
