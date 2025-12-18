[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **models**

---

# Models 模块文档

## 模块职责

`models` 模块定义应用的数据库模型（ORM Models），使用 SQLAlchemy 映射数据库表结构。该模块是数据持久化层的核心，所有数据库操作都基于这些模型进行。

## 入口与启动

### 模型导入方式
```python
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.base import Base  # 基类
```

### 数据库表创建
```python
from app.core.database import engine, Base
from app.models import document, chunk  # 导入所有模型以注册

# 创建所有表
Base.metadata.create_all(bind=engine)
```

## 对外接口

### 基础模型类（Base）
**位置**: `app/models/base.py`
**状态**: 空文件，待实现
**建议实现**:
```python
from app.core.database import Base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### Document 模型（待实现）
**位置**: `app/models/document.py`
**状态**: 空文件
**职责**: 存储文档元数据

**建议实现**:
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from app.core.database import Base
from datetime import datetime
import enum

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50))
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    collection_name = Column(String(255), nullable=False)  # Milvus 集合名
    upload_time = Column(DateTime, default=datetime.utcnow)
    processed_time = Column(DateTime, nullable=True)
    error_message = Column(String(1024), nullable=True)

    # 关系
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
```

### Chunk 模型（待实现）
**位置**: `app/models/chunk.py`
**状态**: 空文件
**职责**: 存储文档分块信息

**建议实现**:
```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String(255), nullable=True)  # Milvus 中的向量 ID
    metadata = Column(JSON, nullable=True)  # 额外的元数据（如页码、标题等）

    # 关系
    document = relationship("Document", back_populates="chunks")

    # 索引
    __table_args__ = (
        Index('idx_document_chunk', 'document_id', 'chunk_index'),
    )
```

## 关键依赖与配置

### 外部依赖
- **SQLAlchemy** (>=2.0.25): ORM 框架
- **PyMySQL** (>=1.1.0): MySQL 驱动

### 数据库表设计原则
1. **主键**: 所有表使用自增整型主键 `id`
2. **外键**: 使用 `ForeignKey` 定义关系，设置 `ondelete` 行为
3. **索引**: 为常用查询字段添加索引
4. **枚举**: 状态字段使用 SQLAlchemy Enum
5. **时间戳**: 记录创建和更新时间
6. **软删除**: 可选，通过 `is_deleted` 字段实现

### 表关系设计
```
Document (1) ←→ (N) Chunk
一个文档对应多个分块
```

## 数据模型

### 建议的数据库 Schema

#### documents 表
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 主键 | PRIMARY KEY, AUTO_INCREMENT |
| filename | VARCHAR(255) | 文件名 | NOT NULL |
| file_path | VARCHAR(512) | 文件存储路径 | NOT NULL |
| file_size | INT | 文件大小（字节） | NOT NULL |
| file_type | VARCHAR(50) | 文件类型（pdf/docx） | |
| status | ENUM | 处理状态 | DEFAULT 'pending' |
| collection_name | VARCHAR(255) | Milvus 集合名 | NOT NULL |
| upload_time | DATETIME | 上传时间 | DEFAULT CURRENT_TIMESTAMP |
| processed_time | DATETIME | 处理完成时间 | NULL |
| error_message | VARCHAR(1024) | 错误信息 | NULL |

#### chunks 表
| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INT | 主键 | PRIMARY KEY, AUTO_INCREMENT |
| document_id | INT | 文档外键 | FOREIGN KEY, NOT NULL |
| chunk_index | INT | 分块序号 | NOT NULL |
| content | TEXT | 文本内容 | NOT NULL |
| vector_id | VARCHAR(255) | Milvus 向量 ID | NULL |
| metadata | JSON | 额外元数据 | NULL |

#### 索引设计
```sql
-- documents 表
CREATE INDEX idx_filename ON documents(filename);
CREATE INDEX idx_status ON documents(status);
CREATE INDEX idx_upload_time ON documents(upload_time);

-- chunks 表
CREATE INDEX idx_document_chunk ON chunks(document_id, chunk_index);
CREATE INDEX idx_vector_id ON chunks(vector_id);
```

## 测试与质量

### 当前测试覆盖
- **单元测试**: 无
- **模型测试**: 无

### 测试建议

#### 模型创建测试
```python
def test_create_document(db_session):
    doc = Document(
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        collection_name="test_collection"
    )
    db_session.add(doc)
    db_session.commit()
    assert doc.id is not None
```

#### 关系测试
```python
def test_document_chunks_relationship(db_session):
    doc = Document(filename="test.pdf", ...)
    db_session.add(doc)
    db_session.commit()

    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="Test content"
    )
    db_session.add(chunk)
    db_session.commit()

    assert len(doc.chunks) == 1
    assert doc.chunks[0].content == "Test content"
```

#### 级联删除测试
```python
def test_cascade_delete(db_session):
    doc = Document(filename="test.pdf", ...)
    chunk = Chunk(document_id=doc.id, ...)
    db_session.add_all([doc, chunk])
    db_session.commit()

    db_session.delete(doc)
    db_session.commit()

    assert db_session.query(Chunk).count() == 0
```

## 常见问题 (FAQ)

### Q1: 如何执行数据库迁移？
A: 建议使用 Alembic：
```bash
# 初始化
alembic init alembic

# 生成迁移文件
alembic revision --autogenerate -m "create documents and chunks tables"

# 执行迁移
alembic upgrade head
```

### Q2: 如何添加新字段？
A: 修改模型后，使用 Alembic 生成迁移脚本，或在测试环境中删除表重建。

### Q3: 如何处理大文本内容？
A: 使用 `Text` 类型而非 `String`，MySQL 会自动选择 TEXT/MEDIUMTEXT/LONGTEXT。

### Q4: 如何实现软删除？
A: 添加 `is_deleted` 字段，并在查询时过滤：
```python
class Document(Base):
    # ...
    is_deleted = Column(Boolean, default=False)

# 查询时
docs = db.query(Document).filter(Document.is_deleted == False).all()
```

### Q5: 如何优化查询性能？
A:
1. 为常用查询字段添加索引
2. 使用 `lazy="select"` 或 `lazy="joined"` 优化关系加载
3. 使用 `with_entities()` 仅查询需要的字段

## 相关文件清单

### 待实现文件
- `/home/yl/yl/wy/rag/rag_project/app/models/base.py` (空文件)
  - 建议实现时间戳混入类
  - 建议实现软删除混入类

- `/home/yl/yl/wy/rag/rag_project/app/models/document.py` (空文件)
  - 需实现 Document 模型
  - 定义文档元数据字段
  - 定义与 Chunk 的关系

- `/home/yl/yl/wy/rag/rag_project/app/models/chunk.py` (空文件)
  - 需实现 Chunk 模型
  - 定义分块数据字段
  - 定义与 Document 的关系

### 包标识文件
- `app/models/__init__.py`

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 models 模块文档
- 发现所有模型文件为空，待实现
- 提供了 Document 和 Chunk 的完整实现建议
- 建议集成 Alembic 迁移工具

---

## 下一步建议

### 立即优先级（必须实现）
1. **实现 Document 模型**:
   - 定义所有必需字段
   - 添加文档状态枚举
   - 定义与 Chunk 的一对多关系

2. **实现 Chunk 模型**:
   - 定义分块存储字段
   - 添加外键关联
   - 创建组合索引

3. **创建数据库表**:
   ```python
   from app.core.database import engine, Base
   from app.models import document, chunk
   Base.metadata.create_all(bind=engine)
   ```

### 短期优先级
1. 集成 Alembic 数据库迁移工具
2. 实现 base.py 中的混入类（TimestampMixin）
3. 添加模型单元测试
4. 编写数据库初始化脚本

### 中期优先级
1. 实现软删除功能
2. 添加模型方法（如 `to_dict()`）
3. 优化索引设计
4. 实现审计日志（记录模型变更）
