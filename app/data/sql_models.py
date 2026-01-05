from sqlalchemy import Column, String, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from chatbot.rag.app.core.database import Base

# 1. 映射旧表 (只读用，或者用于外键关联)
class UserProfileOld(Base):
    __tablename__ = "user_profiles"
    # 必须与数据库实际结构一致，否则报错
    id = Column(Integer, primary_key=True)
    city = Column(String(50))
    # 其他字段如 gender, age 可以按需添加，不加也不影响关联查询

# 2. 定义新关联表 (存储 RAG 特征)
class RagUserTraits(Base):
    __tablename__ = "rag_user_traits"

    # 使用 user_id 作为主键，并作为外键关联旧表的 id
    user_id = Column(Integer, ForeignKey("user_profiles.id"), primary_key=True)
    
    static_tags = Column(JSON, default=list)      # 例如: ["python", "ai"]
    dynamic_interests = Column(JSON, default=list)# 例如: ["concurrency", "optimization"]
    negative_tags = Column(JSON, default=list)    # 例如: ["politics"]
    
    # 可选：建立关系，方便 ORM 查询
    # base_profile = relationship("UserProfileOld", backref="rag_traits")
