# 依赖注入（如获取 DB 会话）
from app.core.database import SessionLocal

# 这是一个生成器函数
def get_db():
    db = SessionLocal()  # 1. 建立连接
    try:
        yield db         # 2. 把连接“借”给接口用（暂停在这里）
    except Exception:
        # 如果请求处理过程中抛异常，Session 可能处于“未提交/无效事务”状态。
        # rollback 可以避免后续复用连接时出现 PendingRollbackError。
        db.rollback()
        raise
    finally:
        db.close()       # 3. 等接口用完了，自动回来执行这一行，关闭连接