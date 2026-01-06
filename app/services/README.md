# 同义词功能模块结构

## 目录结构

```
app/
├── models/                    # 【数据库层】(SQLAlchemy)
│   └── synonym.py            # 定义MySQL表结构（SynonymGroup, SynonymTerm, SynonymCandidate）
│
├── schemas/                   # ■【契约层】(Pydantic)
│   └── synonym_schema.py     # 定义接口返回给前端的JSON格式
│
├── services/                  # *【业务逻辑层】
│   ├── synonym_service.py    # 同义词业务逻辑（数据访问、查询改写、初始化）
│   └── synonym_mining.py      # 同义词挖掘逻辑
│
└── api/v1/endpoints/         # 【接口路由层】
    ├── synonym.py           # 同义词管理接口
    └── synonym_mining.py    # 同义词挖掘接口
```

## 层级说明

### 1. 数据库层 (models/)
- **文件**: `app/models/synonym.py`
- **职责**: 定义SQLAlchemy ORM模型，对应MySQL表结构
- **包含**: SynonymGroup, SynonymTerm, SynonymCandidate

### 2. 契约层 (schemas/)
- **文件**: `app/schemas/synonym_schema.py`
- **职责**: 定义Pydantic模型，规范API请求/响应的JSON格式
- **包含**: SynonymGroupSchema, SynonymTermSchema, SynonymCandidateSchema等

### 3. 业务逻辑层 (services/)
- **synonym_service.py**: 核心业务逻辑
  - SynonymService: 同义词管理服务（数据访问、添加、导入、删除、查询改写、初始化）
  - ReviewService: 候选审核服务
  
- **synonym_mining.py**: 同义词挖掘逻辑
  - MiningJobScheduler: 挖掘任务调度器
  - IMiningStrategy: 挖掘策略接口
  - LocalEmbeddingMiner: 基于Embedding的挖掘实现
  - SearchLogMiner: 基于搜索日志的挖掘实现

### 4. 接口路由层 (api/)
- **synonym.py**: 同义词管理接口
  - `GET /api/v1/synonyms/groups` - 查询同义词组列表
  - `POST /api/v1/synonyms/manual_upsert` - 手动添加同义词
  - `POST /api/v1/synonyms/batch_import` - 批量导入
  - `DELETE /api/v1/synonyms/groups` - 删除同义词组
  - `GET /api/v1/synonyms/candidates` - 查看候选
  - `POST /api/v1/synonyms/candidates/approve` - 审核通过
  - `POST /api/v1/synonyms/candidates/reject` - 审核拒绝

- **synonym.py**: 同义词管理接口（包含查询改写）
  - `POST /api/v1/synonyms/rewrite` - 查询改写

- **synonym_mining.py**: 同义词挖掘接口
  - `POST /api/v1/synonyms/mining/run` - 启动挖掘任务

## 数据流向

```
API请求 → api/v1/endpoints/synonym.py
         ↓
业务逻辑 → services/synonym_service.py
         ↓
数据访问 → services/synonym_service.py (内部方法)
         ↓
数据库   → models/synonym.py (SQLAlchemy)
         ↓
返回数据 → schemas/synonym_schema.py (Pydantic)
         ↓
JSON响应 → API返回
```

## 导入示例

```python
# 在api层使用
from app.services.synonym_service import SynonymService, ReviewService

# 在services层使用
from app.services.synonym_service import SynonymService
from app.services.synonym_mining import MiningJobScheduler
```

## 数据库迁移

数据库建表语句位于 `app/models/synonym.sql`，执行方式：

```bash
mysql -u rag_user -p rag_data < app/models/synonym.sql
```
