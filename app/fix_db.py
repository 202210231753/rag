import sys
import os
from sqlalchemy import text

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from chatbot.rag.app.core.database import engine, Base
from chatbot.rag.app.data.sql_models import UserProfileModel

def reset_db_table():
    print("=== 重置 MySQL 表结构 ===")
    
    # 1. 删除旧表 (如果存在)
    with engine.connect() as conn:
        print("正在删除旧的 user_profiles 表...")
        conn.execute(text("DROP TABLE IF EXISTS user_profiles"))
        conn.commit()
    
    # 2. 重新创建表
    print("正在重新创建表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 表结构重置完成。")

if __name__ == "__main__":
    reset_db_table()

