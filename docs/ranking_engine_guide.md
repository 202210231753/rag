# 排序引擎使用说明

## 概述

排序引擎提供**黑名单过滤**、**MMR多样性控制**、**位置插入规则**三大功能，用于优化搜索结果排序。

---

## 功能说明

### 1. **黑名单过滤**
- 自动过滤掉被拉黑的文档
- 存储在 Redis 中，实时生效
- 支持批量添加/删除

### 2. **MMR 多样性控制**
- 使用 MMR (最大边际相关性) 算法打散相似文档
- lambda 参数控制相关性与多样性的平衡：
  - `lambda=0`: 只看多样性（不考虑相关性）
  - `lambda=1`: 只看相关性（不考虑多样性）
  - `lambda=0.5`: 平衡模式（推荐）

### 3. **位置插入规则**
- 可以强制将某个文档插入到指定位置
- 支持按查询关键词匹配规则
- 存储在 Redis 中，实时生效

---

## 安装与初始化

### 1. 安装 Redis 依赖
```bash
pip install redis[hiredis]>=5.0.0
```

### 2. 配置环境变量
在 `.env` 文件中添加：
```env
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 可选
```

### 3. 初始化数据库表
执行 SQL 脚本：
```bash
mysql -u root -p rag_data < migrations/001_create_diversity_config.sql
```

### 4. 启动 Redis
```bash
# 如果使用 Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或者使用本地 Redis
redis-server
```

---

## API 使用示例

### 基础 URL
```
http://localhost:8000/api/v1/ranking
```

---

## 1. Lambda 参数管理

### 获取当前 Lambda 参数
```bash
curl -X GET http://localhost:8000/api/v1/ranking/lambda
```

**响应示例：**
```json
{
  "lambda_param": 0.5,
  "updated_at": "2026-01-12 15:30:00"
}
```

### 更新 Lambda 参数
```bash
curl -X PUT http://localhost:8000/api/v1/ranking/lambda \
  -H "Content-Type: application/json" \
  -d '{"lambda_param": 0.7}'
```

**参数说明：**
- `lambda_param`: 0-1 之间的浮点数
  - 越接近 0，越重视多样性
  - 越接近 1，越重视相关性

---

## 2. 黑名单管理

### 添加黑名单
```bash
curl -X POST http://localhost:8000/api/v1/ranking/blacklist \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add",
    "doc_ids": ["doc_123", "doc_456"]
  }'
```

**响应示例：**
```json
{
  "action": "add",
  "affected_count": 2,
  "total_count": 5
}
```

### 移除黑名单
```bash
curl -X POST http://localhost:8000/api/v1/ranking/blacklist \
  -H "Content-Type: application/json" \
  -d '{
    "action": "remove",
    "doc_ids": ["doc_123"]
  }'
```

### 查询黑名单列表
```bash
curl -X GET http://localhost:8000/api/v1/ranking/blacklist
```

**响应示例：**
```json
["doc_123", "doc_456", "doc_789"]
```

---

## 3. 位置插入规则

### 设置位置规则
```bash
curl -X POST http://localhost:8000/api/v1/ranking/position \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能",
    "doc_id": "doc_999",
    "position": 0
  }'
```

**参数说明：**
- `query`: 查询关键词（会转为小写匹配）
- `doc_id`: 要插入的文档ID
- `position`: 目标位置（0-based，0表示置顶）

**响应示例：**
```json
{
  "query": "人工智能",
  "doc_id": "doc_999",
  "position": 0
}
```

### 查询所有位置规则
```bash
curl -X GET http://localhost:8000/api/v1/ranking/position
```

**响应示例：**
```json
{
  "人工智能": {
    "doc_id": "doc_999",
    "position": 0
  },
  "机器学习": {
    "doc_id": "doc_888",
    "position": 1
  }
}
```

### 删除位置规则
```bash
curl -X DELETE http://localhost:8000/api/v1/ranking/position/人工智能
```

---

## 4. 搜索接口（集成排序引擎）

### 执行搜索
```bash
curl -X POST http://localhost:8000/api/v1/search/multi-recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能",
    "top_n": 10,
    "recall_top_k": 100,
    "enable_rerank": false,
    "enable_ranking": true
  }'
```

**参数说明：**
- `enable_ranking`: 是否启用排序引擎（默认true）

**执行流程（enable_ranking=true）：**
1. 多路召回
2. RRF 融合
3. 可选重排
4. **黑名单过滤**
5. **MMR 多样性控制**
6. **位置插入规则**
7. 返回最终结果

---

## 使用场景示例

### 场景 1: 过滤低质量内容
```bash
# 将低质量文档加入黑名单
curl -X POST http://localhost:8000/api/v1/ranking/blacklist \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add",
    "doc_ids": ["spam_doc_1", "spam_doc_2"]
  }'
```

### 场景 2: 提升结果多样性
```bash
# 调高 lambda 参数，增加多样性
curl -X PUT http://localhost:8000/api/v1/ranking/lambda \
  -H "Content-Type: application/json" \
  -d '{"lambda_param": 0.3}'
```

### 场景 3: 置顶重要文档
```bash
# 为特定查询置顶推广文档
curl -X POST http://localhost:8000/api/v1/ranking/position \
  -H "Content-Type: application/json" \
  -d '{
    "query": "产品介绍",
    "doc_id": "official_doc",
    "position": 0
  }'
```

---

## 常见问题

### Q: Redis 连接失败怎么办？
**A:** 检查 Redis 是否启动，端口是否正确：
```bash
redis-cli ping  # 应返回 PONG
```

### Q: 排序引擎不生效？
**A:** 确认搜索请求中 `enable_ranking=true`，并查看日志：
```bash
tail -f logs/rag.log | grep RankingEngine
```

### Q: 如何禁用排序引擎？
**A:** 搜索时设置 `enable_ranking=false`

### Q: 黑名单立即生效吗？
**A:** 是的，Redis 存储实时生效，无需重启服务

---

## 性能建议

1. **Redis 连接池**: 已自动配置，无需额外设置
2. **Lambda 参数缓存**: 首次读取后会缓存在内存，修改后自动失效
3. **黑名单批量操作**: 尽量批量添加/删除，减少网络开销
4. **位置规则数量**: 建议不超过 100 个，过多会影响查询性能

---

## 监控和日志

### 查看排序引擎日志
```bash
# 过滤排序引擎相关日志
grep "RankingEngine" logs/rag.log

# 实时监控
tail -f logs/rag.log | grep "排序引擎"
```

### 日志示例
```
2026-01-12 15:30:00 | INFO | 🔧 排序引擎开始处理: 输入=10条, query='人工智能'
2026-01-12 15:30:00 | INFO | 🚫 黑名单过滤: 移除 2 条
2026-01-12 15:30:00 | DEBUG | 应用 MMR: lambda=0.5, top_n=10
2026-01-12 15:30:00 | INFO | 📍 应用位置规则: doc=doc_999 -> position 0
2026-01-12 15:30:00 | INFO | ✅ 排序引擎完成: 输出=8条
```

---

## 总结

排序引擎提供了灵活的搜索结果控制能力：
- ✅ **黑名单** - 过滤不想展示的内容
- ✅ **多样性** - 避免结果太单一
- ✅ **位置插入** - 人工干预置顶/推广

所有配置通过 API 动态调整，无需重启服务！
