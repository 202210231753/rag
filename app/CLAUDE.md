[根目录](../CLAUDE.md) > **app**

---

# App 模块文档

## 模块职责

`app` 模块是整个 RAG Knowledge System 的核心应用模块，包含所有业务代码。它遵循分层架构设计，将 API 接口、业务逻辑、数据模型、RAG 引擎等功能进行清晰的模块化划分。

## 入口与启动

### 主入口文件
- **文件路径**: `/home/yl/yl/wy/rag/rag_project/app/main.py`
- **启动命令**: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### 应用配置
```python
app = FastAPI(
    title="RAG Knowledge System",
    description="后端 API 接口文档",
    version="1.0.0"
)
```

### 路由注册
所有 API 路由统一使用 `/api/v1` 前缀：
```python
app.include_router(api_router, prefix="/api/v1")
```

### 健康检查端点
- **路径**: `GET /`
- **响应**: `{"status": "ok", "message": "RAG System is running!"}`

## 对外接口

### API 版本管理
当前支持 API v1，所有端点通过 `/api/v1` 前缀访问。

### 已实现的端点

#### 数据查看模块
- **基础路径**: `/api/v1/viewer`
- **标签**: `数据查看模块`
- **端点**:
  - `GET /api/v1/viewer/list`: 获取文件列表（当前为测试实现）

#### RAG 对话模块（规划中）
- **基础路径**: `/api/v1/chat`（已注释）
- **标签**: `RAG对话模块`
- **状态**: 待实现

### API 文档访问
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 关键依赖与配置

### 外部依赖
- **FastAPI**: Web 框架
- **Uvicorn**: ASGI 服务器
- **LlamaIndex**: RAG 引擎
- **SQLAlchemy**: ORM 框架
- **Pydantic**: 数据验证
- **PyMySQL**: MySQL 驱动
- **Python-dotenv**: 环境变量管理

### 内部模块依赖关系
```
app/
├── main.py              → 依赖 api.v1.router
├── api/                 → API 层
│   ├── deps.py          → 依赖 core.database
│   └── v1/
│       ├── router.py    → 依赖 endpoints
│       └── endpoints/   → 依赖 schemas, services
├── core/                → 核心配置层
│   ├── config.py        → 配置管理（待实现）
│   └── database.py      → 数据库连接
├── models/              → 数据模型层（待实现）
├── schemas/             → 数据验证层（待实现）
├── services/            → 业务逻辑层（待实现）
└── rag/                 → RAG 引擎层（待实现）
```

### 配置文件
- `.env`: 环境变量配置文件（位于项目根目录）
- `requirements.txt`: Python 依赖包列表

## 数据模型

### 当前状态
数据模型文件已创建但尚未实现：
- `/app/models/base.py`: 基础模型类（空文件）
- `/app/models/document.py`: 文件表结构（待实现）
- `/app/models/chunk.py`: 切片表结构（待实现）

### 预期数据模型

#### Document 模型（文档元数据）
建议字段：
- `id`: 主键
- `filename`: 文件名
- `file_path`: 文件路径
- `file_size`: 文件大小
- `upload_time`: 上传时间
- `status`: 处理状态（pending/processing/completed/failed）
- `collection_name`: 对应的 Milvus 集合名

#### Chunk 模型（文档分块）
建议字段：
- `id`: 主键
- `document_id`: 外键关联 Document
- `chunk_index`: 分块序号
- `content`: 文本内容
- `vector_id`: Milvus 中的向量 ID
- `metadata`: JSON 格式的额外信息

## 测试与质量

### 测试文件
- **环境测试**: `/home/yl/yl/wy/rag/rag_project/test_env.py`
  - 测试 LlamaIndex + Milvus + OpenAI 集成
  - 验证异步查询功能

### 测试覆盖缺口
1. 缺少 API 端点的单元测试
2. 缺少数据库模型的测试
3. 缺少服务层的测试
4. 缺少 Schema 验证测试

### 代码质量工具
当前未配置，建议添加：
- `pytest`: 单元测试框架
- `black`: 代码格式化
- `flake8`: 代码风格检查
- `mypy`: 类型检查
- `pytest-cov`: 代码覆盖率

## 常见问题 (FAQ)

### Q1: 如何添加新的 API 端点？
1. 在 `/app/api/v1/endpoints/` 创建新的路由文件
2. 在路由文件中定义 `router = APIRouter()`
3. 在 `/app/api/v1/router.py` 中导入并注册路由

### Q2: 如何使用数据库会话？
使用 FastAPI 的依赖注入：
```python
from app.api import deps
from sqlalchemy.orm import Session

@router.get("/items")
def get_items(db: Session = Depends(deps.get_db)):
    # 使用 db 进行数据库操作
    pass
```

### Q3: 如何配置 LlamaIndex？
在 `/app/core/config.py` 中统一管理配置，或在服务层初始化时配置。

### Q4: 如何处理文件上传？
使用 FastAPI 的 `UploadFile`：
```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    # 处理文件内容
```

## 相关文件清单

### Python 源文件（25 个）
- `app/main.py`: 应用入口
- `app/__init__.py`: 包标识
- `app/core/config.py`: 配置管理（空）
- `app/core/database.py`: 数据库连接
- `app/core/__init__.py`: 包标识
- `app/models/base.py`: 基础模型（空）
- `app/models/document.py`: 文档模型（空）
- `app/models/chunk.py`: 分块模型（空）
- `app/models/__init__.py`: 包标识
- `app/schemas/document_schema.py`: 文档 Schema（空）
- `app/schemas/chat_schema.py`: 对话 Schema（空）
- `app/schemas/__init__.py`: 包标识
- `app/services/rag_service.py`: RAG 服务（空）
- `app/services/viewer_service.py`: 查看服务（空）
- `app/services/__init__.py`: 包标识
- `app/rag/retrievers.py`: 检索器（空）
- `app/rag/__init__.py`: 包标识
- `app/api/deps.py`: 依赖注入
- `app/api/__init__.py`: 包标识
- `app/api/v1/router.py`: 路由汇总
- `app/api/v1/__init__.py`: 包标识
- `app/api/v1/endpoints/chat.py`: 对话端点（空）
- `app/api/v1/endpoints/viewer.py`: 查看端点（测试实现）
- `app/api/v1/endpoints/__init__.py`: 包标识

### 缓存文件（忽略）
- `app/__pycache__/`: Python 字节码缓存

## 变更记录 (Changelog)

### 2025-12-18 15:00:06
- 创建 app 模块文档
- 识别了 25 个 Python 源文件
- 发现多数模块文件为空，处于待实现状态
- 仅 `main.py`, `database.py`, `deps.py`, `router.py`, `viewer.py` 有实现代码

---

## 下一步建议

### 立即优先级
1. **实现数据模型**: 完善 `models/document.py` 和 `models/chunk.py`
2. **实现 Schema**: 完善 `schemas/document_schema.py` 和 `schemas/chat_schema.py`
3. **实现核心服务**: 开发 `services/rag_service.py`

### 短期优先级
1. 实现文档上传 API（chat.py）
2. 实现文档列表查看（viewer.py 完善）
3. 实现 RAG 对话接口

### 中期优先级
1. 添加单元测试
2. 添加日志记录
3. 实现错误处理机制
4. 添加 API 认证
