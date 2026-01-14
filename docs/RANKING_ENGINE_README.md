# 排序引擎 - 快速参考

## 🎯 三大核心功能

| 功能 | 作用 | 存储 | 实时性 |
|-----|-----|------|-------|
| **黑名单过滤** | 过滤不想展示的文档 | Redis | 立即生效 |
| **MMR 多样性控制** | 打散相似文档，增加多样性 | MySQL | 修改后生效 |
| **位置插入规则** | 强制插入文档到指定位置 | Redis | 立即生效 |

---

## 📁 新增文件清单

```
app/
├── core/
│   ├── config.py                    # ✅ 新增 Redis 配置
│   └── redis_client.py              # ✨ Redis 客户端封装
├── rag/
│   └── ranking/                     # ✨ 排序引擎模块
│       ├── __init__.py
│       ├── engine.py                # 排序引擎核心
│       └── mmr.py                   # MMR 算法实现
├── api/
│   └── v1/
│       └── endpoints/
│           └── ranking.py           # ✨ 排序管理 API

migrations/
└── 001_create_diversity_config.sql  # ✨ 数据库迁移脚本

docs/
└── ranking_engine_guide.md          # ✨ 详细使用指南

test_ranking_engine.py               # ✨ 功能测试脚本
start_ranking_engine.sh              # ✨ 快速启动脚本
```

---

## 🚀 快速启动

### 1. 安装依赖
```bash
source .venv/bin/activate
pip install redis[hiredis]>=5.0.0
```

### 2. 启动 Redis
```bash
# Docker 方式
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或本地方式
redis-server
```

### 3. 初始化数据库
```bash
mysql -u rag_user -prag_password rag_data < migrations/001_create_diversity_config.sql
```

### 4. 启动服务
```bash
./start_ranking_engine.sh
# 或
uvicorn app.main:app --reload
```

### 5. 运行测试
```bash
python test_ranking_engine.py
```

---

## 🔧 API 快速参考

### Lambda 参数
```bash
# 获取
GET /api/v1/ranking/lambda

# 更新
PUT /api/v1/ranking/lambda
{"lambda_param": 0.7}
```

### 黑名单
```bash
# 添加
POST /api/v1/ranking/blacklist
{"action": "add", "doc_ids": ["doc_1", "doc_2"]}

# 移除
POST /api/v1/ranking/blacklist
{"action": "remove", "doc_ids": ["doc_1"]}

# 查询
GET /api/v1/ranking/blacklist
```

### 位置插入
```bash
# 设置规则
POST /api/v1/ranking/position
{"query": "人工智能", "doc_id": "doc_999", "position": 0}

# 查询规则
GET /api/v1/ranking/position

# 删除规则
DELETE /api/v1/ranking/position/{query}
```

### 搜索（集成排序引擎）
```bash
POST /api/v1/search/multi-recall
{
  "query": "测试查询",
  "top_n": 10,
  "enable_ranking": true  # 启用排序引擎
}
```

---

## 🎓 核心算法：MMR

### 公式
```
MMR = λ × 相关性 - (1-λ) × 最大相似度
```

### Lambda 参数
- **λ=0**: 只看多样性 → 结果最分散
- **λ=0.5**: 平衡模式 → **推荐值**
- **λ=1**: 只看相关性 → 结果最相关

### 相似度计算
```python
同类别 (category) → +0.6
同来源 (source)   → +0.4
总分归一化到 [0, 1]
```

---

## 📊 执行流程

```
用户搜索
  ↓
多路召回 + RRF 融合 + 可选重排
  ↓
排序引擎 (enable_ranking=true)
  ├─ 1️⃣ 黑名单过滤 (Redis)
  ├─ 2️⃣ MMR 多样性控制 (Lambda)
  └─ 3️⃣ 位置插入规则 (Redis)
  ↓
最终结果
```

---

## 🐛 常见问题

### Redis 连接失败
```bash
# 检查 Redis
redis-cli ping  # 应返回 PONG

# 查看配置
cat .env | grep REDIS
```

### 排序引擎不生效
```bash
# 查看日志
tail -f logs/rag.log | grep RankingEngine

# 确认参数
curl http://localhost:8000/api/v1/ranking/lambda
```

### 黑名单不生效
```bash
# 检查 Redis
redis-cli
> SMEMBERS blacklist

# 确认搜索参数
enable_ranking: true
```

---

## 📈 性能优化

| 优化项 | 实现方式 | 效果 |
|-------|---------|------|
| Lambda 缓存 | 内存缓存 | 避免重复查询 MySQL |
| Redis 连接池 | 异步连接池 | 高并发支持 |
| 黑名单批量检查 | SMISMEMBER | 减少网络往返 |
| MMR 候选限制 | 只处理前 100 个 | 控制计算量 |

---

## 📚 参考资料

- **详细文档**: `docs/ranking_engine_guide.md`
- **API 文档**: http://localhost:8000/docs
- **测试脚本**: `test_ranking_engine.py`

---

## ✅ 验证清单

- [ ] Redis 已安装并启动
- [ ] 数据库表已创建
- [ ] Redis 依赖已安装
- [ ] 环境变量已配置
- [ ] 服务正常启动
- [ ] API 测试通过

---

**总代码量：~400 行**  
**核心文件：3 个**  
**API 接口：8 个**  

简单、实用、够用！🎉
