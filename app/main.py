# 【入口】整个程序的启动点
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api.v1.router import api_router
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（启动和关闭）。"""
    # 启动时执行（在后台线程执行，不阻塞服务启动）
    import threading
    init_thread = threading.Thread(target=_init_on_startup, daemon=True)
    init_thread.start()
    
    yield
    
    # 关闭时执行（如果需要）
    # _cleanup_on_shutdown()


def _init_on_startup():
    """应用启动时执行初始化。"""
    # 检查是否启用自动初始化（可通过环境变量控制）
    auto_init = os.getenv("SYNONYM_AUTO_INIT", "true").lower() == "true"
    
    if not auto_init:
        logger.info("同义词自动初始化已禁用（SYNONYM_AUTO_INIT=false）")
        return
    
    # 初始化默认同义词数据（如果数据库为空）
    try:
        from app.services.synonym_service import init_synonyms_on_startup
        
        db = SessionLocal()
        try:
            init_synonyms_on_startup(db, domain="default")
        finally:
            db.close()
    except Exception as e:
        # 记录警告但不影响应用启动
        logger.warning(
            f"启动时初始化同义词数据失败（可忽略）: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG)
        )


app = FastAPI(
    title="RAG Knowledge System",
    description="后端 API 接口文档",
    version="1.0.0",
    lifespan=lifespan,  # 使用 lifespan 替代已废弃的 on_event
)

# 注册所有路由，统一加前缀 /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG System is running!"}


@app.get("/synonym-test", response_class=HTMLResponse)
def synonym_test_page():
    """最基本的前端页面：手动测试同义词管理、改写和候选审核等接口。"""
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>同义词模块测试页</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 20px; }
    h1 { font-size: 20px; }
    h2 { font-size: 16px; margin-top: 24px; }
    label { display: inline-block; width: 80px; }
    input, textarea { padding: 4px; margin: 2px 0; width: 260px; }
    button { margin-top: 4px; padding: 4px 10px; }
    .section { border: 1px solid #ddd; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
    pre { background: #f7f7f7; padding: 8px; max-height: 260px; overflow: auto; }
  </style>
</head>
<body>
  <h1>同义词模块最小测试页</h1>
  <p>当前后端 Base URL 默认使用本页所在域（例如 <code>http://localhost:8010/api/v1</code>）。下面所有请求都直接调用后端接口。</p>

  <div class="section">
    <h2>1. 同义词库管理：单条添加 / 批量添加 / 删除</h2>
    <div>
      <label>domain</label>
      <input id="m-domain" value="default" />
    </div>
    <div>
      <label>canonical</label>
      <input id="m-canonical" value="近似" />
    </div>
    <div>
      <label>synonyms</label>
      <input id="m-synonyms" value="相近, 类似, 八九不离十" />
      <div style="font-size:12px;color:#666;">多个同义词用逗号分隔</div>
    </div>
    <button onclick="manualUpsert()">单条添加 / 更新</button>

    <div style="margin-top:10px;">
      <button onclick="listGroups()">列出当前 domain 的前 20 组</button>
      <button onclick="deleteGroups()">删除指定 groupId（逗号分隔）</button>
      <input id="del-ids" placeholder="例如: 1,2,3" style="width:180px;" />
    </div>
  </div>

  <div class="section">
    <h2>2. 查询改写（自动同义词获取）</h2>
    <div>
      <label>domain</label>
      <input id="r-domain" value="default" />
    </div>
    <div>
      <label>query</label>
      <input id="r-query" value="近似" />
    </div>
    <button onclick="rewrite()">调用 /synonyms/rewrite</button>
  </div>

  <div class="section">
    <h2>3. 候选同义词：查看 & 审核通过</h2>
    <div>
      <label>domain</label>
      <input id="c-domain" value="default" />
    </div>
    <button onclick="listCandidates()">查看 pending 候选（前 20）</button>
    <div style="margin-top:8px;">
      <label>candidateIds</label>
      <input id="approve-ids" placeholder="例如: 1,2,3" style="width:200px;" />
    </div>
    <button onclick="approveCandidates()">审核通过</button>
  </div>

  <div class="section">
    <h2>4. 触发离线挖掘（/synonyms/mining/run）</h2>
    <div>
      <label>domain</label>
      <input id="mining-domain" value="default" />
    </div>
    <button onclick="runMining()">运行挖掘任务（默认参数）</button>
  </div>

  <div class="section">
    <h2>接口响应</h2>
    <pre id="output"></pre>
  </div>

  <script>
    const apiBase = window.location.origin + "/api/v1";

    function log(obj) {
      const el = document.getElementById("output");
      el.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
    }

    async function api(path, method, body, params) {
      const url = new URL(apiBase + path);
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined && v !== null && v !== "") url.searchParams.append(k, v);
        });
      }
      const res = await fetch(url.toString(), {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      let data;
      try {
        data = await res.json();
      } catch (e) {
        data = await res.text();
      }
      log({ url: url.toString(), status: res.status, data });
      return { res, data };
    }

    async function manualUpsert() {
      const domain = document.getElementById("m-domain").value.trim();
      const canonical = document.getElementById("m-canonical").value.trim();
      const synonymsStr = document.getElementById("m-synonyms").value.trim();
      const synonyms = synonymsStr.split(",").map(s => s.trim()).filter(Boolean);
      await api("/synonyms/manual_upsert", "POST", { domain, canonical, synonyms });
    }

    async function listGroups() {
      const domain = document.getElementById("m-domain").value.trim();
      await api("/synonyms/groups", "GET", null, { domain, limit: 20, offset: 0 });
    }

    async function deleteGroups() {
      const idsStr = document.getElementById("del-ids").value.trim();
      if (!idsStr) {
        alert("请输入要删除的 groupId 列表");
        return;
      }
      const groupIds = idsStr.split(",").map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
      await api("/synonyms/groups", "DELETE", { groupIds });
    }

    async function rewrite() {
      const domain = document.getElementById("r-domain").value.trim();
      const query = document.getElementById("r-query").value.trim();
      await api("/synonyms/rewrite", "POST", { domain, query });
    }

    async function listCandidates() {
      const domain = document.getElementById("c-domain").value.trim();
      await api("/synonyms/candidates", "GET", null, {
        domain,
        status: "pending",
        limit: 20,
        offset: 0,
      });
    }

    async function approveCandidates() {
      const idsStr = document.getElementById("approve-ids").value.trim();
      if (!idsStr) {
        alert("请输入要审核通过的 candidateId 列表");
        return;
      }
      const ids = idsStr.split(",").map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
      await api("/synonyms/candidates/approve", "POST", { ids });
    }

    async function runMining() {
      const domain = document.getElementById("mining-domain").value.trim();
      await api("/synonyms/mining/run", "POST", null, { domain });
    }
  </script>
</body>
</html>
        """,
        status_code=200,
    )