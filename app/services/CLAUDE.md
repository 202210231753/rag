[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **services**

---

# Services 模块文档

## 模块职责

`services` 模块是业务逻辑层，封装复杂的业务操作，协调多个数据源（MySQL、Milvus、OpenAI）的交互。该模块使 API 端点保持简洁，将核心业务逻辑与接口层解耦。

## 入口与启动

### Service 使用方式
```python
from app.services.rag_service import RAGService
from app.services.viewer_service import ViewerService
from sqlalchemy.orm import Session

# 在 API 端点中使用
@router.post("/query")
def query(request: ChatRequest, db: Session = Depends(deps.get_db)):
    rag_service = RAGService(db)
    response = rag_service.query(request.question, request.collection_name)
    return response
```

### Service 初始化
所有 Service 应接受数据库会话作为构造参数：
```python
class MyService:
    def __init__(self, db: Session):
        self.db = db
```

## 对外接口

### RAG Service（待实现）
**位置**: `app/services/rag_service.py`
**状态**: 空文件
**职责**: RAG 核心业务逻辑

**建议实现**:
```python
from sqlalchemy.orm import Session
from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from app.models.document import Document as DBDocument
from app.models.chunk import Chunk
from app.schemas.chat_schema import ChatRequest, ChatResponse
import time
import os

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = int(os.getenv("MILVUS_PORT", "19530"))

    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        collection_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> int:
        """
        上传并处理文档

        Returns:
            document_id: 创建的文档 ID
        """
        # 1. 保存文件到磁盘
        file_path = self._save_file(file_content, filename)

        # 2. 创建文档记录
        db_doc = DBDocument(
            filename=filename,
            file_path=file_path,
            file_size=len(file_content),
            status="processing",
            collection_name=collection_name
        )
        self.db.add(db_doc)
        self.db.commit()

        try:
            # 3. 解析文档
            documents = self._parse_document(file_path)

            # 4. 连接 Milvus
            vector_store = MilvusVectorStore(
                uri=f"http://{self.milvus_host}:{self.milvus_port}",
                collection_name=collection_name,
                dim=1536,
                overwrite=False
            )

            # 5. 创建索引并存储向量
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )

            # 6. 保存 Chunk 记录（可选）
            # TODO: 从 LlamaIndex 获取实际的 chunk 信息并保存

            # 7. 更新文档状态
            db_doc.status = "completed"
            db_doc.processed_time = datetime.utcnow()
            self.db.commit()

            return db_doc.id

        except Exception as e:
            db_doc.status = "failed"
            db_doc.error_message = str(e)
            self.db.commit()
            raise

    def query(
        self,
        question: str,
        collection_name: str,
        top_k: int = 5,
        temperature: float = 0.7
    ) -> ChatResponse:
        """
        执行 RAG 查询
        """
        start_time = time.time()

        # 1. 连接 Milvus
        vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=collection_name,
            dim=1536
        )

        # 2. 创建查询引擎
        index = VectorStoreIndex.from_vector_store(vector_store)
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            response_mode="compact"
        )

        # 3. 执行查询
        response = query_engine.query(question)

        # 4. 构建响应
        query_time = time.time() - start_time

        return ChatResponse(
            answer=str(response),
            sources=[],  # TODO: 提取来源文档
            query_time=query_time
        )

    def _save_file(self, content: bytes, filename: str) -> str:
        """保存文件到磁盘"""
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def _parse_document(self, file_path: str):
        """解析文档"""
        from llama_index.readers.file import PDFReader

        reader = PDFReader()
        documents = reader.load_data(file_path)
        return documents
```

### Viewer Service（待实现）
**位置**: `app/services/viewer_service.py`
**状态**: 空文件
**职责**: 数据查看和管理逻辑

**建议实现**:
```python
from sqlalchemy.orm import Session
from app.models.document import Document
from app.schemas.document_schema import DocumentResponse, DocumentList
from typing import List

class ViewerService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 10) -> DocumentList:
        """
        获取文档列表
        """
        total = self.db.query(Document).count()
        items = (
            self.db.query(Document)
            .offset(skip)
            .limit(limit)
            .all()
        )

        return DocumentList(
            total=total,
            items=[DocumentResponse.model_validate(item) for item in items],
            page=skip // limit + 1,
            page_size=limit
        )

    def get_by_id(self, document_id: int) -> DocumentResponse:
        """
        根据 ID 获取文档
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        return DocumentResponse.model_validate(doc)

    def delete(self, document_id: int) -> bool:
        """
        删除文档（包括 Milvus 中的向量）
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        # TODO: 从 Milvus 删除对应的向量

        self.db.delete(doc)
        self.db.commit()
        return True

    def get_document_content(self, document_id: int) -> str:
        """
        获取文档原始内容
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        with open(doc.file_path, "r", encoding="utf-8") as f:
            return f.read()
```

## 关键依赖与配置

### 外部依赖
- **LlamaIndex Core** (>=0.10.0): RAG 框架
- **LlamaIndex LLMs OpenAI**: OpenAI LLM 集成
- **LlamaIndex Embeddings OpenAI**: OpenAI Embedding 集成
- **LlamaIndex Vector Stores Milvus**: Milvus 向量库集成
- **LlamaIndex Readers File**: 文件读取器（PDF、DOCX 等）

### 环境变量配置
| 变量名 | 用途 | 示例值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-xxxxx` |
| `MILVUS_HOST` | Milvus 服务器地址 | `localhost` |
| `MILVUS_PORT` | Milvus 端口 | `19530` |

### LlamaIndex 配置

#### 全局配置（建议在 core/config.py 中）
```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# 设置全局 LLM
Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.7)

# 设置全局 Embedding
Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

# 设置分块参数
Settings.chunk_size = 512
Settings.chunk_overlap = 50
```

## 数据模型

### Service 输入输出

#### RAGService
- **输入**: 文件字节流、问题字符串、配置参数
- **输出**: 文档 ID、回答结果、来源文档
- **异常**: 文件解析失败、向量存储失败、查询失败

#### ViewerService
- **输入**: 文档 ID、分页参数
- **输出**: 文档列表、文档详情
- **异常**: 文档不存在、权限不足

## 测试与质量

### 当前测试覆盖
- **单元测试**: 无
- **集成测试**: 环境测试（`test_env.py`）

### 测试建议

#### Service 单元测试
```python
import pytest
from unittest.mock import Mock, patch
from app.services.rag_service import RAGService

@pytest.fixture
def mock_db():
    return Mock()

def test_upload_document(mock_db):
    service = RAGService(mock_db)

    with patch('app.services.rag_service.MilvusVectorStore'):
        doc_id = service.upload_document(
            file_content=b"test content",
            filename="test.pdf",
            collection_name="test"
        )
        assert isinstance(doc_id, int)
```

#### Service 集成测试
```python
def test_rag_query_integration(db_session):
    service = RAGService(db_session)

    # 上传测试文档
    doc_id = service.upload_document(...)

    # 执行查询
    response = service.query("What is FastAPI?", "test_collection")

    assert response.answer is not None
    assert response.query_time > 0
```

## 常见问题 (FAQ)

### Q1: 如何处理大文件上传？
A: 使用流式处理和分块上传：
```python
async def upload_large_file(file: UploadFile):
    chunk_size = 1024 * 1024  # 1MB
    while chunk := await file.read(chunk_size):
        # 处理每个 chunk
        pass
```

### Q2: 如何优化 RAG 查询性能？
A:
1. 调整 `similarity_top_k` 参数
2. 使用缓存存储常见问题的答案
3. 异步处理查询请求
4. 使用更高效的 Embedding 模型

### Q3: 如何处理多语言文档？
A: LlamaIndex 支持多语言，确保 Embedding 模型支持目标语言。

### Q4: 如何实现流式响应？
A: 使用 `StreamingResponse` 和异步生成器：
```python
from fastapi.responses import StreamingResponse

async def stream_response(query: str):
    response = query_engine.stream_chat(query)
    for token in response.response_gen:
        yield token

@router.post("/stream")
async def stream_query(request: ChatRequest):
    return StreamingResponse(
        stream_response(request.question),
        media_type="text/event-stream"
    )
```

### Q5: 如何处理 Service 中的事务？
A: 使用数据库会话的上下文管理：
```python
try:
    # 业务操作
    self.db.add(obj)
    self.db.commit()
except Exception:
    self.db.rollback()
    raise
```

## 相关文件清单

### 待实现文件
- `/home/yl/yl/wy/rag/rag_project/app/services/rag_service.py` (空文件)
  - 需实现文档上传处理
  - 需实现 RAG 查询逻辑
  - 需实现文件解析和向量化

- `/home/yl/yl/wy/rag/rag_project/app/services/viewer_service.py` (空文件)
  - 需实现文档列表查询
  - 需实现文档详情查询
  - 需实现文档删除逻辑

### 包标识文件
- `app/services/__init__.py`

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 services 模块文档
- 发现所有 Service 文件为空，待实现
- 提供了完整的 RAGService 和 ViewerService 实现建议
- 建议集成 LlamaIndex 全局配置

---

## 下一步建议

### 立即优先级（必须实现）
1. **实现 RAGService 核心功能**:
   - `upload_document()`: 文档上传和处理
   - `query()`: RAG 查询
   - `_parse_document()`: 文档解析

2. **实现 ViewerService 基础功能**:
   - `get_all()`: 文档列表查询
   - `get_by_id()`: 文档详情查询
   - `delete()`: 文档删除

3. **集成到 API 端点**:
   - 在 `chat.py` 中使用 RAGService
   - 在 `viewer.py` 中使用 ViewerService

### 短期优先级
1. 添加错误处理和日志记录
2. 实现文件类型验证（仅支持 PDF、DOCX）
3. 添加 Service 单元测试
4. 实现查询结果缓存

### 中期优先级
1. 实现异步 Service 方法
2. 添加批量文档上传
3. 实现 Milvus 集合管理（创建、删除）
4. 添加文档更新和重新索引功能
5. 实现对话历史管理
