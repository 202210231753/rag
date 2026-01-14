from __future__ import annotations

# 数据库连接池生成器
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. 加载环境变量 (.env)
load_dotenv()

# 2. 从环境变量读取配置
USER = os.getenv("DB_USER", "rag_user")
PASSWORD = os.getenv("DB_PASSWORD", "rag_password")
SERVER = os.getenv("DB_SERVER", "localhost")
PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "rag_data")

# 3. 组装 MySQL 连接字符串
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{SERVER}:{PORT}/{DB_NAME}"

# 4. 创建数据库引擎 (Engine)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600,
    pool_pre_ping=True,
)

# 5. Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 6. Base 类（所有 Model 继承它）
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖：提供一个请求级别的 DB Session。

    说明：项目里同时存在 `app/api/deps.py:get_db`，这里保留一份是为了兼容 ingest/knowledge
    模块直接从 `app.core.database` 引用的写法。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
