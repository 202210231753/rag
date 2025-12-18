[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **schemas**

---

# Schemas 模块文档

## 模块职责

`schemas` 模块定义 Pydantic 数据验证模型，用于 API 请求和响应的数据校验、序列化与反序列化。该模块确保数据在进入业务逻辑前已经过严格验证，并为 API 文档提供清晰的数据结构说明。

## 入口与启动

### Schema 导入方式
```python
from app.schemas.document_schema import DocumentResponse, DocumentCreate
from app.schemas.chat_schema import ChatRequest, ChatResponse
```

### 在 API 端点中使用
```python
from fastapi import APIRouter
from app.schemas.document_schema import DocumentResponse

router = APIRouter()

@router.get("/documents/{id}", response_model=DocumentResponse)
def get_document(id: int, db: Session = Depends(deps.get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    return doc  # Pydantic 自动序列化
```

## 对外接口

### Document Schema（待实现）
**位置**: `app/schemas/document_schema.py`
**状态**: 空文件
**职责**: 文档相关的请求/响应模型

**建议实现**:
```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentBase(BaseModel):
    """文档基础字段"""
    filename: str = Field(..., max_length=255, description="文件名")
    file_type: Optional[str] = Field(None, max_length=50, description="文件类型")

class DocumentCreate(DocumentBase):
    """创建文档请求"""
    pass

class DocumentResponse(DocumentBase):
    """文档响应"""
    id: int
    file_path: str
    file_size: int
    status: DocumentStatus
    collection_name: str
    upload_time: datetime
    processed_time: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentList(BaseModel):
    """文档列表响应"""
    total: int
    items: list[DocumentResponse]
    page: int
    page_size: int
```

### Chat Schema（待实现）
**位置**: `app/schemas/chat_schema.py`
**状态**: 空文件
**职责**: 对话相关的请求/响应模型

**建议实现**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ChatRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    collection_name: Optional[str] = Field(None, description="指定搜索的集合")
    top_k: int = Field(5, ge=1, le=20, description="返回的相关文档数量")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成温度")

class SourceDocument(BaseModel):
    """来源文档"""
    document_id: int
    chunk_id: int
    content: str
    score: float = Field(..., description="相似度分数")

class ChatResponse(BaseModel):
    """问答响应"""
    answer: str = Field(..., description="AI 回答")
    sources: List[SourceDocument] = Field(default_factory=list, description="参考来源")
    query_time: float = Field(..., description="查询耗时（秒）")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FileUploadRequest(BaseModel):
    """文件上传元数据"""
    collection_name: str = Field(..., description="Milvus 集合名称")
    chunk_size: int = Field(512, ge=128, le=2048, description="分块大小")
    chunk_overlap: int = Field(50, ge=0, le=500, description="分块重叠")

class FileUploadResponse(BaseModel):
    """文件上传响应"""
    document_id: int
    filename: str
    status: str
    message: str
```

## 关键依赖与配置

### 外部依赖
- **Pydantic** (>=2.5.0): 数据验证框架
- **typing**: Python 类型注解

### Pydantic V2 重要变更
Pydantic V2 与 V1 有重大差异，需注意：

#### 配置类变更
```python
# V1 (旧)
class MySchema(BaseModel):
    class Config:
        orm_mode = True

# V2 (新)
class MySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

#### 验证器变更
```python
# V1 (旧)
from pydantic import validator

@validator('email')
def validate_email(cls, v):
    return v

# V2 (新)
from pydantic import field_validator

@field_validator('email')
@classmethod
def validate_email(cls, v):
    return v
```

### Schema 设计原则
1. **分离关注点**: 区分 Request、Response、Create、Update 等模型
2. **继承复用**: 使用基类避免字段重复
3. **字段验证**: 使用 `Field` 添加约束和描述
4. **可选字段**: 使用 `Optional` 明确可为空
5. **嵌套模型**: 使用复杂类型组合

## 数据模型

### Schema 分类策略

#### 1. Base Schema
定义共享字段，其他 Schema 继承：
```python
class DocumentBase(BaseModel):
    filename: str
    file_type: Optional[str] = None
```

#### 2. Create Schema
用于创建资源的请求：
```python
class DocumentCreate(DocumentBase):
    # 不包含 id, upload_time 等自动生成的字段
    pass
```

#### 3. Update Schema
用于更新资源的请求：
```python
class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    status: Optional[DocumentStatus] = None
```

#### 4. Response Schema
用于 API 响应：
```python
class DocumentResponse(DocumentBase):
    id: int
    upload_time: datetime

    model_config = ConfigDict(from_attributes=True)
```

#### 5. List Schema
用于列表响应（带分页）：
```python
class DocumentList(BaseModel):
    total: int
    items: list[DocumentResponse]
    page: int
    page_size: int
```

## 测试与质量

### 当前测试覆盖
- **单元测试**: 无
- **Schema 验证测试**: 无

### 测试建议

#### Schema 验证测试
```python
import pytest
from pydantic import ValidationError
from app.schemas.document_schema import DocumentCreate

def test_document_create_valid():
    data = {"filename": "test.pdf", "file_type": "pdf"}
    doc = DocumentCreate(**data)
    assert doc.filename == "test.pdf"

def test_document_create_invalid():
    with pytest.raises(ValidationError):
        DocumentCreate(filename="")  # 空字符串应该失败
```

#### 序列化测试
```python
def test_document_response_serialization():
    from app.models.document import Document
    from app.schemas.document_schema import DocumentResponse

    doc = Document(id=1, filename="test.pdf", ...)
    response = DocumentResponse.from_orm(doc)  # V1
    # 或
    response = DocumentResponse.model_validate(doc)  # V2

    assert response.id == 1
    assert response.filename == "test.pdf"
```

#### JSON Schema 生成测试
```python
def test_json_schema():
    from app.schemas.document_schema import DocumentResponse

    schema = DocumentResponse.model_json_schema()
    assert "properties" in schema
    assert "filename" in schema["properties"]
```

## 常见问题 (FAQ)

### Q1: 如何处理 ORM 模型到 Pydantic 的转换？
A: 使用 `from_attributes=True` 配置（V2）或 `orm_mode=True`（V1）：
```python
class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

### Q2: 如何自定义验证逻辑？
A: 使用 `field_validator` 装饰器（V2）：
```python
from pydantic import field_validator

class MySchema(BaseModel):
    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

### Q3: 如何处理日期时间格式？
A: Pydantic 自动处理常见格式，也可自定义：
```python
from datetime import datetime
from pydantic import Field

class MySchema(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Q4: 如何排除某些字段不在响应中返回？
A: 使用 `model_dump(exclude={...})` 方法：
```python
response_data = document.model_dump(exclude={"internal_field"})
```

### Q5: 如何处理文件上传？
A: 文件上传使用 FastAPI 的 `UploadFile`，不需要 Pydantic Schema：
```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
```

## 相关文件清单

### 待实现文件
- `/home/yl/yl/wy/rag/rag_project/app/schemas/document_schema.py` (空文件)
  - 需实现文档相关的所有 Schema
  - DocumentBase, DocumentCreate, DocumentUpdate, DocumentResponse, DocumentList

- `/home/yl/yl/wy/rag/rag_project/app/schemas/chat_schema.py` (空文件)
  - 需实现对话相关的所有 Schema
  - ChatRequest, ChatResponse, FileUploadRequest, FileUploadResponse, SourceDocument

### 包标识文件
- `app/schemas/__init__.py`

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 schemas 模块文档
- 发现所有 Schema 文件为空，待实现
- 提供了完整的 Document 和 Chat Schema 实现建议
- 说明了 Pydantic V2 的重要变更

---

## 下一步建议

### 立即优先级（必须实现）
1. **实现 document_schema.py**:
   - DocumentBase（基类）
   - DocumentCreate（创建请求）
   - DocumentUpdate（更新请求）
   - DocumentResponse（响应）
   - DocumentList（列表响应）

2. **实现 chat_schema.py**:
   - ChatRequest（问答请求）
   - ChatResponse（问答响应）
   - FileUploadRequest（上传元数据）
   - FileUploadResponse（上传响应）
   - SourceDocument（来源文档）

3. **更新 API 端点**:
   - 在 `viewer.py` 中使用 DocumentResponse
   - 在 `chat.py` 中使用 Chat Schema

### 短期优先级
1. 添加 Schema 单元测试
2. 添加自定义验证器（如文件类型验证）
3. 实现分页相关的通用 Schema
4. 添加错误响应 Schema

### 中期优先级
1. 实现 Schema 的示例数据（用于 API 文档）
2. 添加 Schema 之间的转换工具函数
3. 实现复杂的嵌套 Schema（如统计数据）
4. 优化 Schema 的性能（使用 `use_enum_values` 等）
