# 排序引擎实现完成 ✅

## 📋 实现概要

已完成**最小化排序引擎**的实现，包含以下核心功能：

### ✨ 三大核心功能
1. **黑名单过滤** - Redis Set 存储，实时过滤不想展示的文档
2. **MMR 多样性控制** - 使用最大边际相关性算法，打散相似文档
3. **位置插入规则** - Redis Hash 存储，支持按查询强制插入文档

---

## 📁 新增文件列表

### 核心实现（3 个文件）
- `app/rag/ranking/engine.py` - 排序引擎核心逻辑（150 行）
- `app/rag/ranking/mmr.py` - MMR 算法实现（100 行）
- `app/core/redis_client.py` - Redis 客户端封装（150 行）

### API 接口（1 个文件）
- `app/api/v1/endpoints/ranking.py` - 管理 API（200 行）

### 数据库迁移（1 个文件）
- `migrations/001_create_diversity_config.sql` - 多样性配置表

### 配置更新
- `app/core/config.py` - 新增 Redis 配置
- `requirements.txt` - 新增 redis 依赖

### 集成修改
- `app/rag/search_gateway.py` - 集成排序引擎
- `app/api/v1/router.py` - 注册 ranking 路由
- `app/api/deps.py` - 依赖注入排序引擎
- `app/main.py` - 初始化 Redis 连接
- `app/schemas/search_schema.py` - 新增 enable_ranking 参数

### 文档和测试
- `docs/ranking_engine_guide.md` - 详细使用指南
- `RANKING_ENGINE_README.md` - 快速参考文档
- `test_ranking_engine.py` - 功能测试脚本
- `start_ranking_engine.sh` - 快速启动脚本

---

## 🎯 API 接口清单

### Lambda 参数管理（2 个）
- `GET /api/v1/ranking/lambda` - 获取 Lambda 参数
- `PUT /api/v1/ranking/lambda` - 更新 Lambda 参数

### 黑名单管理（2 个）
- `POST /api/v1/ranking/blacklist` - 添加/移除黑名单
- `GET /api/v1/ranking/blacklist` - 查询黑名单列表

### 位置插入规则（3 个）
- `POST /api/v1/ranking/position` - 设置位置规则
- `GET /api/v1/ranking/position` - 查询所有规则
- `DELETE /api/v1/ranking/position/{query}` - 删除规则

### 搜索接口（已更新）
- `POST /api/v1/search/multi-recall` - 新增 `enable_ranking` 参数

---

## 🔄 执行流程

```
用户查询
  ↓
SearchGateway.search()
  ├─ 向量化 + 分词
  ├─ 多路并行召回
  ├─ RRF 融合
  ├─ 可选重排
  ↓
RankingEngine.apply() (如果 enable_ranking=true)
  ├─ 1️⃣ 黑名单过滤 (Redis)
  ├─ 2️⃣ MMR 多样性控制 (Lambda 参数)
  └─ 3️⃣ 位置插入规则 (Redis)
  ↓
返回最终结果
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
source .venv/bin/activate
pip install redis[hiredis]>=5.0.0
```

### 2. 启动 Redis
```bash
# Docker 方式（推荐）
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或本地方式
redis-server
```

### 3. 配置环境变量
在 `.env` 文件中添加（可选，默认值已设置）：
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 4. 初始化数据库表
```bash
mysql -u rag_user -prag_password rag_data < migrations/001_create_diversity_config.sql
```

### 5. 启动服务
```bash
# 使用快速启动脚本
./start_ranking_engine.sh

# 或手动启动
uvicorn app.main:app --reload
```

### 6. 访问 API 文档
打开浏览器访问：http://localhost:8000/docs

### 7. 运行测试
```bash
python test_ranking_engine.py
```

---

## 📖 使用示例

### 示例 1: 添加黑名单
```bash
curl -X POST http://localhost:8000/api/v1/ranking/blacklist \
  -H "Content-Type: application/json" \
  -d '{"action": "add", "doc_ids": ["spam_1", "spam_2"]}'
```

### 示例 2: 调整多样性
```bash
curl -X PUT http://localhost:8000/api/v1/ranking/lambda \
  -H "Content-Type: application/json" \
  -d '{"lambda_param": 0.3}'
```

### 示例 3: 置顶文档
```bash
curl -X POST http://localhost:8000/api/v1/ranking/position \
  -H "Content-Type: application/json" \
  -d '{"query": "产品介绍", "doc_id": "official_doc", "position": 0}'
```

### 示例 4: 搜索（启用排序引擎）
```bash
curl -X POST http://localhost:8000/api/v1/search/multi-recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能",
    "top_n": 10,
    "enable_ranking": true
  }'
```

---

## 🎓 核心算法：MMR

### 算法公式
```
MMR = λ × 相关性分数 - (1-λ) × 最大相似度
```

### Lambda 参数说明
- `λ = 0`: 完全多样性（结果最分散，但可能不相关）
- `λ = 0.5`: **平衡模式（推荐）**
- `λ = 1`: 完全相关性（结果最相关，但可能重复）

### 相似度计算策略
```python
相似度 = 0.0
if 同类别 (metadata.category): 相似度 += 0.6
if 同来源 (metadata.source):  相似度 += 0.4
最终相似度归一化到 [0, 1]
```

---

## ⚡ 性能特性

### 三级缓存架构
```
请求 → 内存缓存 → Redis → MySQL
       (微秒)    (毫秒)  (10ms)
```

### 优化措施
- ✅ Lambda 参数内存缓存
- ✅ Redis 异步连接池
- ✅ 黑名单批量检查 (SMISMEMBER)
- ✅ MMR 计算候选数限制

### 预期性能
- 黑名单过滤：< 5ms
- MMR 重排（100 候选）：< 20ms
- 位置插入：< 2ms
- **总增加延迟：< 30ms**

---

## 🔍 监控和调试

### 查看日志
```bash
# 实时监控排序引擎
tail -f logs/rag.log | grep "RankingEngine"

# 查看 MMR 详情
tail -f logs/rag.log | grep "MMR"
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

## 🧪 测试清单

### 功能测试
- [ ] Lambda 参数读取和更新
- [ ] 黑名单添加、移除、查询
- [ ] 位置规则设置、查询、删除
- [ ] 搜索集成（enable_ranking=true/false）

### 性能测试
- [ ] 并发请求（100 QPS）
- [ ] 黑名单规模（1000+ 文档）
- [ ] MMR 计算时间（100 候选）
- [ ] Redis 连接稳定性

### 降级测试
- [ ] Redis 宕机降级
- [ ] MySQL 查询失败降级
- [ ] MMR 计算超时降级

---

## 📊 数据存储

### MySQL
```sql
-- diversity_config 表
id | lambda_param | updated_at
1  | 0.5         | 2026-01-12 15:30:00
```

### Redis
```
# 黑名单
Key: blacklist (Set)
Value: {"doc_123", "doc_456", ...}

# 位置规则
Key: position_rules:人工智能 (String)
Value: "doc_999:0"
```

---

## 🎉 总结

### 实现特点
- ✅ **极简设计** - 只有 400 行核心代码
- ✅ **模块化** - 每个功能独立可测试
- ✅ **高性能** - 三级缓存 + 异步架构
- ✅ **易扩展** - 清晰的接口和抽象
- ✅ **实时生效** - Redis 存储，无需重启

### 代码统计
- 核心模块：3 个文件，~400 行
- API 接口：8 个端点
- 测试脚本：1 个
- 文档：2 个（详细 + 快速参考）

### 适用场景
- ✅ 过滤低质量/违规内容
- ✅ 增加搜索结果多样性
- ✅ 人工干预置顶/推广
- ✅ 个性化排序策略

---

## 📚 参考文档

1. **快速参考**: `RANKING_ENGINE_README.md`
2. **详细指南**: `docs/ranking_engine_guide.md`
3. **API 文档**: http://localhost:8000/docs
4. **测试脚本**: `test_ranking_engine.py`

---

## 🐛 已知限制

1. **位置规则** - 只支持精确查询匹配（不支持正则）
2. **MMR 相似度** - 只基于 category 和 source 元数据
3. **性能** - MMR 对超大候选集（>1000）可能较慢

### 未来优化方向
- [ ] 位置规则支持正则表达式
- [ ] MMR 相似度支持向量计算
- [ ] 添加排序规则优先级
- [ ] 支持 AB 测试框架

---

**实现完成！准备好接受前端调用了！** 🚀
