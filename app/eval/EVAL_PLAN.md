# Eval 模块开发计划与步骤（解耦框架 + 多评测方式）

> 目标：构建一个高度解耦、可扩展的评测框架，支持多评测方式与多阶段评估（Retrieval / Rerank / Rewrite / Generation 等），同时可接入第三方评测框架（如 ragas），并支持 JSONL 与 CSV 数据格式、统一报告输出。

## 一、目标与范围

### 1. 评测阶段
- Retrieval（Embedding 模型粗排）
- Rerank（精排）
- Rewrite（Query 改写）
- Generation（答案生成）
- End-to-End（检索增强生成完整链路）

### 2. 评测方式
- 支持多种“评测引擎/模式”，可在配置中切换：
  - HTTP API（FastAPI 服务）
  - 直接调用内部模块（内部类/服务层）
  - 第三方评测框架（ragas / 其他）
- 默认优先使用 HTTP API；必要时可切换到内部调用模式（如离线批评测、无服务依赖）

### 3. 数据格式
- 输入：JSONL + CSV
- 输出：JSON/CSV/Markdown 报告

## 二、评测数据规范

### 1. 统一最小字段（适配 JSONL/CSV）
- `id`：样本唯一标识
- `query`：用户查询（非空）
- `answers`：标准答案（可为空，用于 Generation/E2E）
- `relevant_doc_ids`：标准相关文档 ID（可为空，用于 Retrieval/Rerank）
- `relevant_texts`：标准相关文本片段（可为空，用于 Retrieval/Generation）
- `rewrite`：改写后的 Query（可为空，用于 Rewrite）
- `metadata`：业务标签/领域/用户组（可选）

### 2. 阶段增强字段（可选但推荐）
- `candidate_doc_ids`：候选文档 ID 列表（用于 Rerank 离线评测，不依赖 Retrieval）
- `candidate_texts`：候选文本列表（与 candidate_doc_ids 对齐）
- `contexts`：检索到的上下文片段（用于 Generation/E2E 或离线复算）
- `split`：数据集划分标记（train/dev/test），用于可重复评测

### 2. JSONL 示例
```
{"id":"q1","query":"xxx","answers":["..."],"relevant_doc_ids":["1","2"],"relevant_texts":["..."],"rewrite":"...","metadata":{"domain":"finance"}}
```

### 3. CSV 示例（列名）
```
id,query,answers,relevant_doc_ids,relevant_texts,rewrite,metadata
```
- CSV 中的 list 字段使用 JSON 字符串形式存储（如 `["a","b"]`）

## 三、评测指标与评测框架清单

### Retrieval（粗排）
- Recall@K
- MRR
- NDCG@K
- Hit Rate@K
- Context Recall（可选）

### Rerank（精排）
- NDCG@K（小 K）
- Precision@K
- Boost Ratio（与粗排对比）
- Top-1 Accuracy（Hit@1）
> 注：Boost Ratio 需明确 baseline（可来自 retrieval 或固定候选顺序），并在报告中标记对照来源。

### Rewrite
- 语义保留：Embedding Cosine / BERTScore（先用 embedding cosine）
- 检索增益：Recall/NDCG 差值
- Zero-result rate reduction
- Query Clarity（LLM-as-a-Judge，可选）

### Generation
- Faithfulness / Groundedness
- Answer Relevance
- Answer Correctness
- Hallucination Rate
- Context Precision / Relevance（与检索增强强相关）
> 注：LLM-as-a-Judge 指标需记录 prompt 版本、模型与温度，保证可复现。

## 四、模块划分（目录规划与解耦设计）

```
app/eval/
  EVAL_PLAN.md
  core/
    interfaces.py       # 评测引擎/数据源/指标/报告的抽象接口
    registry.py         # 插件注册与发现
    pipeline.py         # 可组合的评测流水线
  datasets/
    loaders.py          # JSONL/CSV 统一读写
    validators.py       # 格式校验
    schema.py           # 标准字段定义与映射
  engines/
    api_engine.py       # HTTP API 调用实现
    internal_engine.py  # 内部模块调用实现
    ragas_engine.py     # ragas 适配器（封装其调用方式）
  metrics/
    retrieval.py        # Recall/MRR/NDCG/HitRate
    rerank.py           # Precision/NDCG/Boost/Top1
    rewrite.py          # 语义保留/增益/清晰度
    generation.py       # Faithfulness/Relevance/Correctness
    e2e.py              # E2E 指标
  runners/
    retrieval_runner.py # retrieval 评测主流程
    rerank_runner.py    # rerank 评测主流程
    rewrite_runner.py   # rewrite 评测主流程
    generation_runner.py# generation 评测主流程
    e2e_runner.py       # RAG 全链路评测
  reports/
    reporter.py         # 汇总输出 JSON/CSV/Markdown
  configs/
    eval_config.yaml    # 评测任务配置（引擎/指标/数据/并发等）
```

## 五、流程与步骤（按优先级）

### Phase 1：框架骨架与可插拔评测引擎
1. 定义统一数据 schema（JSONL/CSV）与字段映射
2. 定义核心接口（Engine / Runner / Metric / Reporter）
3. 实现插件注册与配置驱动（可按配置切换引擎与指标）
4. 实现基础报告输出（JSON + CSV）

### Phase 2：Retrieval 评测（先跑通）
1. 实现 API 引擎（/search/multi-recall）
2. 实现 Retrieval Runner
3. 指标：Recall@K / MRR / NDCG@K / HitRate@K
4. 输出样本级与汇总级结果

### Phase 3：Rewrite 评测（增益指标）
1. 支持 `rewrite` 字段或调用 rewrite API
2. 对原始 query 与 rewrite query 分别执行 Retrieval
3. 计算增益指标（Recall/NDCG 差值）
4. 计算 Zero-result rate reduction
5. 可选：Query Clarity（LLM-as-a-Judge）

### Phase 4：Rerank 评测
1. 引入 rerank API（或 mock）
2. 先走 retrieval 获取候选，再走 rerank
3. 计算 NDCG@K / Precision@K
4. 计算 Boost Ratio
5. 增加 Top-1 Accuracy

### Phase 5：Generation 与 End-to-End 评测
1. 统一输入结构：query + context + answer
2. 支持两种引擎：API 生成 / 内部调用
3. 指标：Faithfulness / Relevance / Correctness / Hallucination
4. End-to-End：加入 E2E Latency / TTFT / Cost per Query

### Phase 6：ragas 与第三方框架适配
1. ragas 适配器（输入格式转换、结果解析）
2. 统一输出格式，纳入 reporter
3. 与自研指标并行输出

## 六、API 调用与引擎适配建议

### 1. Retrieval
- 使用 `/api/v1/search/multi-recall`
- 输入：query + top_n + recall_top_k
- 输出：results + recall_stats

### 2. Rewrite
- 若有 rewrite 服务，走 `/api/v1/...`
- 否则直接使用数据中的 rewrite 字段

### 3. Rerank
- 若有 rerank 服务，走 `/api/v1/...`
- 否则只做 retrieval-level 的 ranking 评测

## 七、并发与稳定性

- API 调用支持并发批量（async / asyncio.gather）
- 记录失败样本与错误原因
- 可配置重试次数 + 超时
- 对外部服务（LLM/Embedding）加入指数退避与熔断策略（避免大面积失败）

## 八、可复现性与对照

- 评测记录需要落地：config 快照、数据集 hash、模型/版本号、评测时间
- 对照评测需明确 baseline 来源（如：上一个版本 / 固定配置）
- 结果统计同时输出 macro/micro 平均与分桶统计（按 metadata）

## 九、结果输出格式

### 1. 每条样本级别结果
- id, query, metrics, latency, hit/miss
- 可选字段：engine_type、error_reason、raw_payload（便于追踪）

### 2. 汇总级别
- 平均指标 + 分位数
- 按 metadata 分桶统计（可选）
- 失败率、空结果率、超时率统计

## 十、里程碑（建议）

- M1：框架骨架 + 可插拔引擎/指标 + 报告输出
- M2：Retrieval eval 跑通
- M3：Rewrite eval + 增益指标
- M4：Rerank eval + Boost/Top1
- M5：Generation + End-to-End
- M6：ragas 适配并纳入统一报告

---

如需调整：请说明 API 具体路径、返回字段结构、以及是否需要接入鉴权。

### 第三方评测框架（补充说明）
- ragas：Faithfulness, Answer Relevancy, Context Precision/Recall, Context Relevancy
- 可扩展：trulens / phoenix / deepeval 等（仅作为适配层，不耦合核心）
