[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **core**

---

# Core 模块文档

## 模块职责

`core` 模块负责提供应用的核心基础设施，包括配置管理、数据库连接、认证机制等底层功能。这是整个应用的基石，其他所有模块都依赖于此模块提供的基础服务。

## 入口与启动

### 模块加载
`core` 模块通过 `__init__.py` 自动加载，其他模块通过以下方式引用：
```python
from app.core.database import SessionLocal, engine, Base
from app.core import config  # 待实现
```

### 初始化顺序
1. 加载环境变量（`.env` 文件）
2. 创建数据库引擎（Engine）
3. 创建会话工厂（SessionLocal）
4. 定义基础模型类（Base）

## 对外接口

### 数据库连接接口

#### SessionLocal
**类型**: `sessionmaker`
**用途**: 数据库会话工厂，用于创建数据库会话
**使用方式**:
```python
from app.core.database import SessionLocal

db = SessionLocal()
try:
    # 执行数据库操作
    pass
finally:
    db.close()
```

#### engine
**类型**: `Engine`
**用途**: SQLAlchemy 数据库引擎
**使用场景**:
- 创建数据库表：`Base.metadata.create_all(bind=engine)`
- 执行原生 SQL
- 数据库迁移工具集成

#### Base
**类型**: `DeclarativeMeta`
**用途**: 所有 ORM 模型的基类
**使用方式**:
```python
from app.core.database import Base
from sqlalchemy import Column, Integer, String

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
```

### 配置管理接口（待实现）

预期在 `config.py` 中提供：
- 应用配置类（继承 Pydantic BaseSettings）
- 全局配置实例
- 环境变量验证

## 关键依赖与配置

### 外部依赖
- **SQLAlchemy** (>=2.0.25): ORM 框架
- **PyMySQL** (>=1.1.0): MySQL 驱动
- **cryptography**: PyMySQL 加密支持
- **python-dotenv** (>=1.0.0): 环境变量加载

### 数据库连接配置

#### 环境变量
从 `.env` 文件读取以下配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DB_USER` | `rag_user` | MySQL 用户名 |
| `DB_PASSWORD` | `rag_password` | MySQL 密码 |
| `DB_SERVER` | `localhost` | MySQL 服务器地址 |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_NAME` | `rag_data` | 数据库名称 |

#### 连接字符串格式
```
mysql+pymysql://{USER}:{PASSWORD}@{SERVER}:{PORT}/{DB_NAME}
```

#### 连接池配置
- `pool_recycle=3600`: 每小时回收连接，防止 MySQL 空闲断开
- `pool_pre_ping=True`: 使用前 ping 数据库，确保连接有效

### 配置文件位置
- **环境变量文件**: `/home/yl/yl/wy/rag/rag_project/.env`
- **数据库配置**: `/home/yl/yl/wy/rag/rag_project/app/core/database.py`
- **应用配置**: `/home/yl/yl/wy/rag/rag_project/app/core/config.py`（空文件，待实现）

## 数据模型

### Base 类说明
`Base` 是通过 `declarative_base()` 创建的基类，所有数据库模型必须继承此类。

### 表创建
使用以下代码创建所有数据库表：
```python
from app.core.database import engine, Base
from app.models import document, chunk  # 导入所有模型

Base.metadata.create_all(bind=engine)
```

### 数据库迁移（建议）
当前项目未使用迁移工具，建议集成 **Alembic**：
```bash
pip install alembic
alembic init alembic
```

## 测试与质量

### 当前测试覆盖
- **数据库连接测试**: 通过 `test_env.py` 间接测试
- **单元测试**: 无

### 测试建议

#### 数据库连接测试
```python
def test_database_connection():
    from app.core.database import engine
    connection = engine.connect()
    assert connection is not None
    connection.close()
```

#### 会话工厂测试
```python
def test_session_factory():
    from app.core.database import SessionLocal
    db = SessionLocal()
    assert db is not None
    db.close()
```

### 代码质量
- **类型注解**: 部分缺失，建议补全
- **文档字符串**: 缺失，建议添加
- **错误处理**: 无，建议添加连接失败处理

## 常见问题 (FAQ)

### Q1: 如何切换到不同的数据库？
A: 修改 `.env` 中的 `DB_SERVER`, `DB_PORT`, `DB_NAME` 等配置项，或修改 `database.py` 中的连接字符串格式以支持其他数据库（如 PostgreSQL）。

### Q2: 为什么会出现 "MySQL server has gone away" 错误？
A: 通常是因为连接空闲时间过长被 MySQL 服务器断开。已通过 `pool_recycle=3600` 和 `pool_pre_ping=True` 配置缓解此问题。

### Q3: 如何在 Docker 环境中连接数据库？
A: 将 `DB_SERVER` 设置为 `mysql_db`（Docker Compose 服务名），而非 `localhost`。

### Q4: 如何添加数据库连接日志？
A: 在创建 engine 时添加 `echo=True` 参数：
```python
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=True  # 打印所有 SQL 语句
)
```

### Q5: 为什么 config.py 是空的？
A: 该文件尚未实现。建议使用 Pydantic Settings 实现统一的配置管理。

## 相关文件清单

### 已实现文件
- `/home/yl/yl/wy/rag/rag_project/app/core/database.py` (38 行)
  - 数据库连接配置
  - SessionLocal 会话工厂
  - Base 基类定义
  - 环境变量加载

### 待实现文件
- `/home/yl/yl/wy/rag/rag_project/app/core/config.py` (空文件)
  - 建议实现全局配置管理
  - 使用 Pydantic BaseSettings

### 依赖文件
- `/home/yl/yl/wy/rag/rag_project/.env`
  - 环境变量配置

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 core 模块文档
- 识别 database.py 已完整实现
- 发现 config.py 待实现
- 建议集成配置管理和数据库迁移工具

---

## 下一步建议

### 高优先级
1. **实现 config.py**: 使用 Pydantic Settings 统一管理配置
   ```python
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):
       db_user: str
       db_password: str
       db_server: str
       db_port: int
       db_name: str
       openai_api_key: str
       milvus_host: str
       milvus_port: int

       class Config:
           env_file = ".env"

   settings = Settings()
   ```

2. **添加日志配置**: 在 core 模块中统一配置日志

### 中优先级
1. 集成 Alembic 数据库迁移工具
2. 添加数据库连接池监控
3. 实现数据库健康检查接口

### 低优先级
1. 支持多数据库配置（读写分离）
2. 添加 Redis 缓存连接管理
3. 实现分布式配置中心集成
