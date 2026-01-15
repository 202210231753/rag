[根目录](../../CLAUDE.md) > [app](../CLAUDE.md) > **api**

---

# API 模块文档

## 模块职责

`api` 模块是应用的接口层，负责处理所有 HTTP 请求和响应。它遵循 RESTful 设计原则，提供版本化的 API 端点，并通过依赖注入实现与底层服务的解耦。

## 入口与启动

### 路由注册流程
```
app/main.py
    ↓
include_router(api_router, prefix="/api/v1")
    ↓
app/api/v1/router.py
    ↓
include_router(viewer.router, prefix="/viewer")
include_router(chat.router, prefix="/chat")  # 已注释
```

### API 版本管理
- **当前版本**: v1
- **URL 前缀**: `/api/v1`
- **版本策略**: URL 路径版本控制

## 对外接口

### 已实现的 API 端点

#### 健康检查
- **路径**: `GET /`
- **位置**: `app/main.py`
- **响应**:
  ```json
  {
    "status": "ok",
    "message": "RAG System is running!"
  }
  ```

#### 数据查看模块
- **基础路径**: `/api/v1/viewer`
- **标签**: `数据查看模块`

##### 获取文件列表
- **端点**: `GET /api/v1/viewer/list`
- **参数**:
  - `skip`: int = 0 (分页偏移)
  - `limit`: int = 10 (每页数量)
  - `db`: Session (依赖注入)
- **响应**: `list` (当前返回测试数据 `["test1", "test2"]`)
- **状态**: 测试实现，待完善

#### 智能推荐模块
- **基础路径**: `/api/v1/recommender`
- **标签**: `智能推荐模块`
- **状态**: ✅ 已实现

已实现端点：
- `POST /api/v1/recommender/content`: 获取个性化内容推荐
- `POST /api/v1/recommender/query`: 获取相关查询推荐
- `GET /api/v1/recommender/health`: 推荐服务健康检查

详细使用文档：[RECOMMENDER_API_GUIDE.md](./RECOMMENDER_API_GUIDE.md)

### 规划中的 API 端点

#### RAG 对话模块（已注释）
- **基础路径**: `/api/v1/chat`
- **标签**: `RAG对话模块`
- **状态**: 代码已注释，待实现

预期端点：
- `POST /api/v1/chat/upload`: 上传文档
- `POST /api/v1/chat/query`: 智能问答
- `GET /api/v1/chat/history`: 获取对话历史

### API 文档
FastAPI 自动生成的交互式文档：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 关键依赖与配置

### 依赖注入

#### get_db (数据库会话)
**位置**: `app/api/deps.py`
**类型**: Generator[Session, None, None]
**用途**: 为每个请求提供独立的数据库会话

**实现原理**:
```python
def get_db():
    db = SessionLocal()  # 1. 创建会话
    try:
        yield db             # 2. 提供给路由使用
    finally:
        db.close()           # 3. 请求结束后自动关闭
```

**使用示例**:
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.api import deps

@router.get("/items")
def get_items(db: Session = Depends(deps.get_db)):
    # db 会话在函数结束后自动关闭
    items = db.query(Item).all()
    return items
```

### 路由模块结构
```
api/
├── deps.py                    # 依赖注入
├── RECOMMENDER_API_GUIDE.md   # 推荐 API 使用指南
├── v1/
│   ├── router.py              # 路由汇总
│   └── endpoints/
│       ├── viewer.py          # 数据查看端点
│       ├── recommender.py     # 智能推荐端点 ✅
│       └── chat.py            # 对话端点（空）
```

### 配置项
- **响应模型**: 通过 `response_model` 参数指定
- **标签分组**: 通过 `tags` 参数实现文档分组
- **URL 前缀**: 通过 `prefix` 参数设置

## 数据模型

### 请求/响应 Schema
当前使用原生类型，建议改用 Pydantic 模型：

#### 建议的 Schema 定义
```python
# app/schemas/viewer_schema.py
from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    filename: str
    upload_time: datetime
    status: str

    class Config:
        from_attributes = True

# app/api/v1/endpoints/viewer.py
@router.get("/list", response_model=list[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(deps.get_db)
):
    # 实现逻辑
    pass
```

## 测试与质量

### 当前测试覆盖
- **单元测试**: 无
- **集成测试**: 无
- **手动测试**: 可通过 Swagger UI 测试

### 测试建议

#### API 端点测试
使用 FastAPI 的 TestClient：
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_list_documents():
    response = client.get("/api/v1/viewer/list?skip=0&limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

#### 依赖注入测试
覆盖依赖以使用测试数据库：
```python
from app.api import deps

def override_get_db():
    # 返回测试数据库会话
    pass

app.dependency_overrides[deps.get_db] = override_get_db
```

### 代码质量检查
- **类型注解**: 部分缺失
- **文档字符串**: viewer.py 有简单注释
- **错误处理**: 缺失，建议添加异常处理器

## 常见问题 (FAQ)

### Q1: 如何添加新的 API 端点？
1. 在 `app/api/v1/endpoints/` 创建新文件（如 `documents.py`）
2. 定义路由和处理函数
3. 在 `app/api/v1/router.py` 中导入并注册

### Q2: 如何实现 API 认证？
使用 FastAPI 的依赖注入机制：
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    # 验证 token 逻辑
    if not valid:
        raise HTTPException(status_code=401)
    return user
```

### Q3: 如何处理跨域请求（CORS）？
在 `app/main.py` 中添加：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q4: 如何实现请求日志记录？
使用 FastAPI 的中间件：
```python
import logging
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"{request.method} {request.url}")
    response = await call_next(request)
    return response
```

### Q5: 为什么 chat.py 的路由被注释了？
可能是因为该功能尚未实现或正在开发中。需要实现完整的 RAG 服务后再启用。

## 相关文件清单

### 已实现文件
- `/home/yl/yl/cms/chatbot/rag/app/api/deps.py` (10 行)
  - `get_db()` 依赖注入函数

- `/home/yl/yl/cms/chatbot/rag/app/api/v1/router.py` (13 行)
  - API 路由汇总
  - viewer 路由注册
  - recommender 路由注册 ✅
  - chat 路由注册（已注释）

- `/home/yl/yl/cms/chatbot/rag/app/api/v1/endpoints/viewer.py` (22 行)
  - `GET /list` 端点（测试实现）

- `/home/yl/yl/cms/chatbot/rag/app/api/v1/endpoints/recommender.py` (约 200 行) ✅
  - `POST /content` 内容推荐端点
  - `POST /query` 查询推荐端点
  - `GET /health` 健康检查端点
  - 完整的依赖注入和错误处理

- `/home/yl/yl/cms/chatbot/rag/app/schemas/recommender_schema.py` (约 150 行) ✅
  - `ContentRecommendRequest/Response` Schema
  - `QueryRecommendRequest/Response` Schema
  - `ItemResponse`, `ExplanationItemResponse` Schema
  - `ErrorResponse` Schema

- `/home/yl/yl/cms/chatbot/rag/app/api/RECOMMENDER_API_GUIDE.md` ✅
  - 完整的推荐 API 使用文档
  - Python/JavaScript 调用示例
  - 集成建议和最佳实践

- `/home/yl/yl/cms/chatbot/rag/test_recommender_api.py` ✅
  - API 测试脚本
  - CURL 命令示例

### 待实现文件
- `/home/yl/yl/cms/chatbot/rag/app/api/v1/endpoints/chat.py` (空文件)
  - 文档上传端点
  - 智能问答端点
  - 对话历史端点

### 包标识文件
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `app/api/v1/endpoints/__init__.py`

## 变更记录 (Changelog)

### 2026-01-14
- ✅ **实现智能推荐模块 API**
  - 创建 `recommender.py` 端点（内容推荐、查询推荐、健康检查）
  - 创建 `recommender_schema.py` 定义所有请求/响应 Schema
  - 在 `router.py` 中注册推荐路由
  - 创建完整的使用文档 `RECOMMENDER_API_GUIDE.md`
  - 创建测试脚本 `test_recommender_api.py`
- 支持的功能：
  - 个性化内容推荐（基于用户画像、混合检索、多样性优化）
  - 相关查询推荐（算法匹配 + 热搜 + 精选）
  - 完整的错误处理和日志追踪（trace_id）

### 2025-12-18 15:00:06
- 创建 API 模块文档
- 识别了 3 个已实现文件和 1 个空文件
- viewer.py 有基础实现，chat.py 待开发
- 依赖注入机制已完善

---

## 下一步建议

### 高优先级
1. **实现 chat.py 端点**:
   - 文档上传接口（支持文件上传和解析）
   - 智能问答接口（集成 RAG 服务）

2. **完善 viewer.py**:
   - 接入真实数据库查询
   - 使用 Pydantic Schema 定义响应模型
   - 实现分页、筛选、排序功能

3. **添加错误处理**:
   - 统一异常处理器
   - 自定义错误响应格式

### 中优先级
1. 实现 API 认证和权限控制
2. 添加请求/响应日志
3. 实现 API 限流（Rate Limiting）
4. 添加 CORS 配置

### 低优先级
1. 实现 WebSocket 支持（流式响应）
2. 添加 API 性能监控
3. 实现 API 版本弃用机制
4. 添加 GraphQL 支持（可选）
