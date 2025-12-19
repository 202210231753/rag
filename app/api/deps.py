# 依赖注入（如获取 DB 会话）
from app.core.database import SessionLocal

# 这是一个生成器函数
def get_db():
    db = SessionLocal()  # 1. 建立连接
    try:
        yield db         # 2. 把连接“借”给接口用（暂停在这里）
    finally:
        db.close()       # 3. 等接口用完了，自动回来执行这一行，关闭连接