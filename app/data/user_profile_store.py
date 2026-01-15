from typing import Dict, List
from sqlalchemy.orm import Session
from chatbot.rag.app.data.models import UserProfile
from chatbot.rag.app.data.sql_models import RagUserTraits, UserProfileOld
from chatbot.rag.app.core.database import SessionLocal, engine, Base

class UserProfileStore:
    def __init__(self):
        # 确保新表存在 (旧表假设已存在)
        Base.metadata.create_all(bind=engine)

    def load(self, user_id: str) -> UserProfile:
        """
        加载用户画像。
        user_id: 必须是能转换为 int 的字符串 (因为旧表 id 是 int)
        """
        db: Session = SessionLocal()
        try:
            # 尝试转换 ID
            try:
                uid_int = int(user_id)
            except ValueError:
                # 如果传入 "user_123" 这种非数字ID，肯定查不到，直接返回空画像
                return UserProfile(user_id=user_id)

            # 1. 查旧表 (获取位置信息)
            old_profile = db.query(UserProfileOld).filter(UserProfileOld.id == uid_int).first()
            
            # 2. 查新表 (获取 RAG 特征)
            traits = db.query(RagUserTraits).filter(RagUserTraits.user_id == uid_int).first()
            
            # 3. 组装
            loc = old_profile.city if old_profile else ""
            
            static = traits.static_tags if traits else []
            dynamic = traits.dynamic_interests if traits else []
            negative = traits.negative_tags if traits else []
            
            return UserProfile(
                user_id=user_id,
                static_tags=static or [],
                location=loc or "",
                negative_tags=negative or [],
                dynamic_interests=dynamic or []
            )
        finally:
            db.close()

    def save(self, profile: UserProfile) -> None:
        """
        保存 RAG 特征到新表 (如果不修改旧表的基本信息，则确保旧表存在该用户)
        """
        db: Session = SessionLocal()
        try:
            try:
                uid_int = int(profile.user_id)
            except ValueError:
                print(f"[Warning] 无法保存用户 {profile.user_id}: ID 不是数字，无法关联旧表")
                return

            # 1. 检查并确保旧表(user_profiles)存在该用户
            # 如果不存在，则创建一个基础记录，以满足外键约束
            user_exists = db.query(UserProfileOld).filter(UserProfileOld.id == uid_int).first()
            if not user_exists:
                print(f"[Info] 用户 {uid_int} 在 user_profiles 中不存在，正在自动创建...")
                new_user = UserProfileOld(id=uid_int, city=profile.location)
                db.add(new_user)
                db.flush() # 立即执行插入，确保后续外键有效
            
            # 2. 保存/更新 RAG 特征
            traits = db.query(RagUserTraits).filter(RagUserTraits.user_id == uid_int).first()
            if not traits:
                traits = RagUserTraits(user_id=uid_int)
                db.add(traits)
            
            traits.static_tags = profile.static_tags
            traits.dynamic_interests = profile.dynamic_interests
            traits.negative_tags = profile.negative_tags
            
            db.commit()
            db.refresh(traits)
        except Exception as e:
            db.rollback()
            print(f"[Error] 保存画像失败: {e}")
            raise e
        finally:
            db.close()

    def batch_save(self, profiles: List[UserProfile]) -> None:
        # 简单循环调用 save，生产环境可用 bulk_save_objects 优化
        for p in profiles:
            self.save(p)
