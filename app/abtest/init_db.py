"""ABTest 模块建表脚本。

用法：
/home/yl/yl/jzz/conda/envs/all-in-rag/bin/python -m app.abtest.init_db

注意：需要先在 rag/.env 配好 DB_USER/DB_PASSWORD/DB_SERVER/DB_PORT/DB_NAME。
"""

from app.core.database import Base, engine

# 确保模型被导入后注册到 Base.metadata
from app.models import abtest  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("[abtest] tables ensured")


if __name__ == "__main__":
    main()
