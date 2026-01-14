# Intervention (敏感词/白名单)

本目录为“敏感词干预 + 白名单干预”的独立实现，设计目标：
- 不修改现有主程序/路由文件（按你的约束），只通过新增模块提供能力；
- 满足“干预后 5 分钟内生效”：通过 TTL=300s 的进程内缓存实现，并在写入后立即 `invalidate()`，做到更快生效。

## 功能覆盖

- 白名单库：单条/批量 upsert、批量删除、查询用户状态（locked/unlocked）
- 敏感词库：单条/批量 upsert、批量删除、命中检测（Aho-Corasick），按 level 分层策略（mask/refuse/...）
- 自动挖掘：基于 n-gram 频次的候选挖掘，落库为 pending，支持 approve/reject

## 如何建表

- `python scripts/init_intervention_db.py`

## 如何接入 FastAPI

你当前的 `api_router` 未引入这些 router（且你要求不改现有文件），所以这里只提供可插拔 router：
- `app.intervention.routers.whitelist:router`
- `app.intervention.routers.censor:router`

如果未来允许改 1 行路由汇总文件，可将其 include 进 `/api/v1`。
