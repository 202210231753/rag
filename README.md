# 同义词功能模块

RAG 系统中的同义词管理功能，支持查询扩展、同义词挖掘和候选审核。

## 快速开始

### 环境部署

```bash
# 1. 创建conda环境
conda create -n rag_env python=3.10
conda activate rag_env

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp env.example .env
# 编辑 .env 文件，配置数据库密码等
```

### 启动服务

```bash
# 启动数据库服务（MySQL）
docker-compose up -d mysql_db

# 启动后端服务
uvicorn app.main:app --reload --port 8888
```

### 访问服务

- **API文档**: http://localhost:8888/docs
- **健康检查**: http://localhost:8888/

## 核心功能

- **手动添加同义词**：通过API添加同义词组
- **批量导入**：支持JSON/CSV/XLSX格式批量导入
- **查询改写**：自动扩展查询词为同义词列表
- **候选审核**：人工审核自动挖掘的同义词候选
- **同义词挖掘**：从搜索日志和文档中自动发现同义词
- **领域隔离**：支持多领域同义词库

## API接口

### 同义词管理
- `GET /api/v1/synonyms/groups` - 查询同义词组列表
- `POST /api/v1/synonyms/manual_upsert` - 手动添加同义词
- `POST /api/v1/synonyms/batch_import` - 批量导入同义词（JSON）
- `POST /api/v1/synonyms/batch_import_file` - 批量导入同义词（文件上传）
- `DELETE /api/v1/synonyms/groups` - 删除同义词组

### 候选审核
- `GET /api/v1/synonyms/candidates` - 查看候选同义词
- `POST /api/v1/synonyms/candidates/approve` - 审核通过候选
- `POST /api/v1/synonyms/candidates/reject` - 审核拒绝候选

### 查询改写
- `POST /api/v1/synonyms/rewrite` - 查询改写（调试用）

### 同义词挖掘
- `POST /api/v1/synonyms/mining/run` - 启动挖掘任务

详细API文档请访问：http://localhost:8888/docs

## 项目结构

```
rag/
├── app/                        # 应用代码
│   ├── api/v1/endpoints/      # API 路由
│   │   ├── synonym.py         # 同义词管理 + 查询改写接口
│   │   └── synonym_mining.py  # 同义词挖掘接口
│   ├── models/                # 数据模型（数据库层，SQLAlchemy）
│   │   └── synonym.py         # SynonymGroup / SynonymTerm / SynonymCandidate
│   ├── services/              # 业务逻辑层
│   │   ├── synonym_service.py # 同义词业务逻辑（增删改查、批量导入、改写）
│   │   └── synonym_mining.py  # 挖掘任务与策略
│   └── schemas/               # Pydantic 数据模型
│       └── synonym_schema.py
├── app/services/README.md     # 同义词模块内部结构说明
├── migrations/                # 同义词相关建表脚本（历史备份）
├── README_同义词数据获取.md   # 同义词数据源与导入说明
├── requirements.txt           # 依赖列表
└── docker-compose.yml         # 启动 MySQL 等依赖服务
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_synonym.py -v
```

## 配置说明

主要配置项（`.env` 文件）：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=rag_user
DB_PASSWORD=your_password
DB_NAME=rag_data

# 同义词功能配置
SYNONYM_AUTO_INIT=true  # 启动时自动初始化默认同义词
```

## 常见问题

### 服务无法启动
- 检查数据库连接是否正常
- 检查环境变量是否正确配置
- 检查端口是否被占用

### 同义词不生效
- 检查同义词组是否已启用
- 检查领域（domain）是否匹配
- 检查查询改写是否被调用

更多问题请参考 [功能说明文档](docs/功能说明.md) 和 [测试与演示文档](docs/测试与演示.md)。

---
