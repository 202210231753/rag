import sys
import os
import json

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.database import Base, SessionLocal, engine
from app.data.sql_models import RagUserTraits, UserProfileOld

# 确保表存在
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    try:
        users_data = [
            {
                "id": 1, "city": "Shanghai", 
                "static": ["python", "ai", "coding", "machine learning"],
                "dynamic": ["transformer models", "langchain tutorial"],
                "negative": ["java", "c#"]
            },
            {
                "id": 2, "city": "Beijing",
                "static": ["travel", "food", "photography"],
                "dynamic": ["japan visa", "sushi restaurants"],
                "negative": ["hiking"]
            },
            {
                "id": 3, "city": "Shenzhen",
                "static": ["gaming", "esports", "hardware"],
                "dynamic": ["rtx 5090 release date", "elden ring dlc"],
                "negative": ["mobile games"]
            },
            {
                "id": 4, "city": "Hangzhou",
                "static": ["fitness", "yoga", "health"],
                "dynamic": ["low carb diet", "home workout"],
                "negative": ["fast food"]
            },
            {
                "id": 5, "city": "New York",
                "static": ["finance", "stocks", "investment"],
                "dynamic": ["fed rate cut", "nvda stock"],
                "negative": ["crypto"]
            },
            {
                "id": 6, "city": "London",
                "static": ["music", "guitar", "rock"],
                "dynamic": ["fender stratocaster", "concert tickets"],
                "negative": ["pop music"]
            },
            {
                "id": 7, "city": "Tokyo",
                "static": ["anime", "manga", "cosplay"],
                "dynamic": ["one piece latest chapter", "akihabara shops"],
                "negative": []
            },
            {
                "id": 8, "city": "Paris",
                "static": ["art", "museums", "history"],
                "dynamic": ["louvre tickets", "impressionism"],
                "negative": ["modern art"]
            },
            {
                "id": 9, "city": "Berlin",
                "static": ["techno", "clubbing", "nightlife"],
                "dynamic": ["berghain queue", "dj sets"],
                "negative": []
            },
            {
                "id": 10, "city": "San Francisco",
                "static": ["startup", "tech", "venture capital"],
                "dynamic": ["y combinator application", "saas metrics"],
                "negative": ["corporate jobs"]
            }
        ]

        print(f"Starting to seed {len(users_data)} users...")

        for u in users_data:
            uid = u["id"]
            
            # 1. 插入或更新 user_profiles
            user = db.query(UserProfileOld).filter(UserProfileOld.id == uid).first()
            if not user:
                user = UserProfileOld(id=uid, city=u["city"])
                db.add(user)
                print(f"Created UserProfileOld: {uid}")
            else:
                user.city = u["city"]
                print(f"Updated UserProfileOld: {uid}")
            
            db.flush()

            # 2. 插入或更新 rag_user_traits
            traits = db.query(RagUserTraits).filter(RagUserTraits.user_id == uid).first()
            if not traits:
                traits = RagUserTraits(
                    user_id=uid,
                    static_tags=u["static"],
                    dynamic_interests=u["dynamic"],
                    negative_tags=u["negative"]
                )
                db.add(traits)
                print(f"Created RagUserTraits: {uid}")
            else:
                traits.static_tags = u["static"]
                traits.dynamic_interests = u["dynamic"]
                traits.negative_tags = u["negative"]
                print(f"Updated RagUserTraits: {uid}")

        db.commit()
        print("Seed data completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()





