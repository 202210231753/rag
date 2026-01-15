import sys
import os
import json

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.database import SessionLocal
from app.data.sql_models import RagUserTraits, UserProfileOld

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}")

def check_data():
    db = SessionLocal()
    try:
        # 查询旧表
        print_separator("Table: user_profiles (Main Table)")
        users = db.query(UserProfileOld).all()
        if not users:
            print("No data found.")
        else:
            print(f"Total records: {len(users)}")
            for u in users:
                print(f"- ID: {u.id}, City: {u.city}")

        # 查询新表
        print_separator("Table: rag_user_traits (RAG Extension)")
        traits = db.query(RagUserTraits).all()
        if not traits:
            print("No data found.")
        else:
            print(f"Total records: {len(traits)}")
            for t in traits:
                print(f"- User ID: {t.user_id}")
                print(f"  Static Tags: {json.dumps(t.static_tags, ensure_ascii=False)}")
                print(f"  Dynamic Interests: {json.dumps(t.dynamic_interests, ensure_ascii=False)}")
                print(f"  Negative Tags: {json.dumps(t.negative_tags, ensure_ascii=False)}")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_data()





