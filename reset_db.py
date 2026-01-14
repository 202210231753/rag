from sqlalchemy import create_engine, text
from app.core.config import settings

DB_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_SERVER}:{settings.DB_PORT}/{settings.DB_NAME}"
engine = create_engine(DB_URL)

def reset_tables():
    with engine.connect() as conn:
        print("🗑️  正在删除旧表 chunks 和 documents...")
        # 先删 chunks (因为它有外键指向 documents)
        conn.execute(text("DROP TABLE IF EXISTS chunks"))
        conn.execute(text("DROP TABLE IF EXISTS documents"))
        conn.commit()
        print("✅ 旧表已删除。下次运行测试脚本时会自动重建新表。")

if __name__ == "__main__":
    reset_tables()
