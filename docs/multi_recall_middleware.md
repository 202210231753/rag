# 多路召回模块中间件接入与验证手册

> 适用对象：需要把 `app/rag/search_gateway.py` 多路召回能力作为 FastAPI 中间件/依赖集成到业务项目的工程师。

---

## 1. 模块全景

- **网关编排**：`SearchGateway` 负责并行触发所有召回策略，并使用 `RRFMergeImpl` 做 Reciprocal Rank Fusion（`app/rag/search_gateway.py`）。
- **服务中间件层**：`EmbeddingService`（OpenAI 向量）、`TokenizerService`（Jieba 分词）提供通用能力，在 `app/api/deps.py` 中通过 `lru_cache` 形成中间件单例。
- **召回策略层**：`VectorRecallStrategy`（Milvus 向量）与 `KeywordRecallStrategy`（ElasticSearch BM25）均实现 `IRecallStrategy` 接口，方便横向扩展。
- **基础设施层**：`VectorDBClient`、`SearchEngineClient` 负责与 Milvus/ElasticSearch 通信，配置由 `app/core/config.py` 管理。

---

## 2. 多路召回 Mermaid 架构图

```mermaid
flowchart LR
    classDef api fill:#E8F4FF,stroke:#1E88E5,stroke-width:1px,color:#0D47A1;
    classDef svc fill:#FFF4E5,stroke:#FB8C00,stroke-width:1px,color:#E65100;
    classDef infra fill:#E8F5E9,stroke:#43A047,stroke-width:1px,color:#1B5E20;
    classDef fusion fill:#F3E5F5,stroke:#8E24AA,stroke-width:1px,color:#4A148C;
    classDef rerank fill:#FCE4EC,stroke:#D81B60,stroke-width:1px,color:#880E4F;

    User((Client\nQuery)):::api --> API{{FastAPI Router\nPOST /api/v1/search/multi-recall}}:::api
    API --> Ctx[SearchGateway\n创建 SearchContext\n(embedding + tokenizer)]:::svc
    Ctx -->|向量| VectorRecall[VectorRecallStrategy\nMilvus 向量召回]:::svc
    Ctx -->|关键词| KeywordRecall[KeywordRecallStrategy\nElasticSearch BM25]:::svc
    VectorRecall --> Milvus[(Milvus\nCollection: documents)]:::infra
    KeywordRecall --> ES[(ElasticSearch\nIndex: rag_documents)]:::infra
    VectorRecall --> Merge
    KeywordRecall --> Merge
    Merge[RRFMergeImpl\n1/(60+rank)]:::fusion --> OptionalRerank{{IRerankService?\n(预留)}}:::rerank
    OptionalRerank --> Result[SearchResult\nresults + recall_stats]:::api
    Merge --> Result
    Result --> API
    API --> User
```

---

## 3. 中间件接入步骤

### 3.1 启动依赖中间件

1. **本地 Docker**：直接复用仓库根目录 `docker-compose.yml`，会拉起 Milvus 全家桶、ElasticSearch 以及 MySQL。
   ```bash
   docker-compose up -d
   ```
   - Compose 会自动把 `backend` 容器中的 `MILVUS_HOST`、`ES_HOST` 改为服务名，外部调用时保持 `.env` 中的 `localhost` 即可。
2. **远程服务**：把实际地址写入 `.env`，并根据需要启用 `MILVUS_SECURE`、`ES_SCHEME=https`、`ES_USERNAME/ES_PASSWORD` 等字段。

### 3.2 FastAPI 依赖注入（中间件入口）

1. **构建网关单例**：按照 `app/api/deps.py` 第 33-76 行的示例，使用 `@lru_cache()` 缓存 `get_search_gateway`，内部实例化所有服务与策略。
2. **暴露依赖**：在任意 FastAPI 端点中通过 `Depends(get_search_gateway)` 获取网关实例，等同于把多路召回能力作为中间件注入。

```python
from fastapi import Depends
from app.api.deps import get_search_gateway
from app.schemas.search_schema import SearchRequest

@router.post("/multi-recall")
async def multi_recall(request: SearchRequest, gateway = Depends(get_search_gateway)):
    return await gateway.search(
        query=request.query,
        top_n=request.top_n,
        recall_top_k=request.recall_top_k,
        enable_rerank=request.enable_rerank,
    )
```

> 任何额外的业务路由也可以共享同一个 SearchGateway，从而把它视作“中间件”注入链路的一部分。

### 3.3 扩展召回策略

1. 新建一个实现 `IRecallStrategy` 的类（例如 `HybridRecallStrategy`），内部接第三方检索。
2. 在 `get_search_gateway()` 内把新的策略 append 到 `recall_strategies` 列表即可。
3. `RRFMergeImpl` 会自动把新增策略的结果纳入融合，无需改动 API。

### 3.4 接入观测与熔断（可选）

- `SearchGateway` 在每个阶段都打印 `loguru` 日志，可在 `app/core/config.py` 设置 `LOG_LEVEL`、`LOG_FILE`。
- 若需要对外暴露 Prometheus、链路追踪，可在 FastAPI 层面加 ASGI 中间件；对 `SearchGateway` 本身无需修改。

---

## 4. 使用说明

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
2. **运行后端**：
   ```bash
   uvicorn app.main:app --reload
   ```
3. **请求示例**：
   ```bash
   curl -X POST http://localhost:8000/api/v1/search/multi-recall \
     -H "Content-Type: application/json" \
     -d '{
       "query": "如何提升企业知识库召回率？",
       "top_n": 5,
       "recall_top_k": 120,
       "enable_rerank": false
     }'
   ```
4. **典型响应**（`SearchResult` 来自 `app/rag/models/search_result.py`）：
   ```json
   {
     "query": "如何提升企业知识库召回率？",
     "results": [
       {"doc_id": "doc_001", "score": 0.0331, "content": "……", "metadata": {"source": "ppt"}}
     ],
     "total": 5,
     "took_ms": 142.6,
     "recall_stats": {"vector": 120, "keyword": 120, "merged": 5}
   }
   ```

---

## 5. 配置清单（节选自 `app/core/config.py`）

| 分类 | 变量 | 默认值 | 作用 |
|------|------|--------|------|
| OpenAI | `OPENAI_API_KEY` | 无 | 向量化与大模型鉴权，必须设置 |
| OpenAI | `OPENAI_EMBEDDING_MODEL` | `text-embedding-ada-002` | 查询向量模型，可替换为兼容模型 |
| Milvus | `MILVUS_HOST`/`MILVUS_PORT` | `localhost`/`19530` | 向量库连接入口 |
| Milvus | `MILVUS_USER`/`MILVUS_PASSWORD` | `None` | 远程环境的认证信息 |
| ElasticSearch | `ES_HOST`/`ES_PORT`/`ES_SCHEME` | `localhost`/`9200`/`http` | BM25 关键词检索 |
| ElasticSearch | `ES_INDEX_NAME` | `rag_documents` | 默认索引名，Mermaid 中也一致 |
| 日志 | `LOG_LEVEL`/`LOG_FILE` | `INFO`/`None` | 控制 loguru 输出级别与落盘位置 |

> 所有变量均读取 `.env`，在 Docker 模式下通过 `env_file` 自动注入，并允许在 `docker-compose.yml` 中覆盖。

---

## 6. 验证与测试报告

| 验证项 | 方法/命令 | 结果 | 说明 |
|--------|-----------|------|------|
| 模块语法验证 | `python -m compileall app/rag app/api app/services app/core` | ✅ 通过 | 所有模块可编译，未发现语法错误 |
| RRF 融合算法 | 手动构造向量/关键词召回列表，计算 1/(60+rank) 对比实现 | ✅ 一致 | 详见 `VERIFICATION_REPORT.md` 中“RRF 融合算法验证” |
| FastAPI 路由健康度 | `GET /`、`GET /api/v1/search/health` | ✅ 200 OK | 详见 `VERIFICATION_REPORT.md` “API 端点验证” |
| SearchGateway 注入 | FastAPI `@router.post("/multi-recall")` + `Depends(get_search_gateway)` | ✅ 运行中 | 依赖注入与 DI 中间件链已在 `app/api/v1/endpoints/search.py` 定义 |

### 6.1 最新验证输出

```bash
$ python -m compileall app/rag app/api app/services app/core
Listing 'app/rag'...
...
Listing 'app/core'...
```
**结果**：命令成功退出（状态码 0），说明所有模块均可在当前环境下通过字节码编译。

### 6.2 参考历史验证

- `VERIFICATION_REPORT.md` 记录了更完整的手工验证矩阵（导入测试、RRF 计算、API 健康检查等），可以作为集成测试的基线。
- 若需要端到端验证，请按报告中的建议启动 Milvus/ElasticSearch/OpenAI 真实服务后，执行 `POST /api/v1/search/multi-recall` 自测。

---

## 7. 常见问题与排查

| 问题 | 排查建议 |
|------|----------|
| Milvus/ES 无法连接 | 确认 `.env` 中地址端口与 Docker 服务名一致；远程场景需开放安全组 |
| 请求耗时异常 | 检查 OpenAI API 配额、Milvus `nprobe` 参数与 ElasticSearch 索引是否命中 |
| 召回列表为空 | 查看日志中 `tokenizer`/`embedding` 输出，确认 query 是否被过滤；必要时调低 `recall_top_k` 做快速验证 |

---

> 有任何新的业务场景，只需在 `recall_strategies` 中增删策略，并复用本手册即可快速完成集成 (￣▽￣)ゞ
