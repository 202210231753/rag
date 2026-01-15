"""完整链路 smoke test：

- 单个 RAG + AB + 大模型 实验：
    - 创建 / 启动 RAG 场景的 AB 实验；
    - 通过 /chat 走 RAG 对话并完成 AB 分流；
    - 注入一些虚拟请求与指标数据（REQUEST / CSAT），模拟真实流量；
    - 对指标做分析；
    - 调用报告生成接口，由大模型输出终版结论并写入数据库；
    - 通过 GET /reports 验证网页端能看到大模型结论。

前置条件：
1) 已初始化 AB 实验相关表：
   python -m app.abtest.init_db

2) 已启动 API 服务（端口 8001）：
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

3) （可选）已启动 Qwen3-4B vLLM OpenAI 兼容服务（端口 8000），用于生成 llmFinalReport：
   见 README 中的 Qwen3-4B 运行命令。

运行本脚本：
   python scripts/full_ab_rag_llm_smoke_test.py
"""

from __future__ import annotations

import json
import random
import time

import requests


ABTEST_BASE = "http://127.0.0.1:8001/api/v1/abtest"
CHAT_BASE = "http://127.0.0.1:8001/api/v1/chat"
RAG_EXPERIMENT_ID = "rag_chat_prompt_v1"


def _pp(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _print_response(r: requests.Response) -> None:
    try:
        payload = r.json()
        _pp(payload)
    except Exception:
        print(f"[http] status={r.status_code}")
        text = (r.text or "").strip()
        print(text[:2000])
        raise


def ensure_rag_experiment_exists() -> None:
    """幂等创建/启动 RAG 对话实验 rag_chat_prompt_v1。"""

    print(f"\n[RAG-0] ensure RAG experiment {RAG_EXPERIMENT_ID} exists")

    # 先尝试创建，如果已存在会返回 409，我们当做成功
    r = requests.post(
        f"{ABTEST_BASE}/experiments",
        json={
            "experimentId": RAG_EXPERIMENT_ID,
            "name": "RAG 对话 AB 实验",
            "observedMetrics": ["REQUEST", "CSAT"],
            "routingVariables": [
                "tenant_id",
                "scene",
                "kb_id",
                "query_category",
            ],
            "stagedWeights": [{"A": 50, "B": 50}],
        },
        timeout=10,
    )
    try:
        payload = r.json()
    except Exception:
        payload = {"code": r.status_code, "msg": r.text}
    print("[RAG-0] create response:")
    _pp(payload)

    # 无论是否已存在，都再调用一次 start，保证处于 STARTED 状态
    print("\n[RAG-0] start RAG experiment")
    r = requests.post(f"{ABTEST_BASE}/experiments/{RAG_EXPERIMENT_ID}/start", timeout=10)
    _print_response(r)


def run_rag_ab_llm_experiment() -> None:
    """单个 RAG+AB+LLM 实验全链路：对话 + 虚假数据 + 分析 + 报告。"""

    ensure_rag_experiment_exists()

    print("\n[RAG-1] send RAG chat requests (with AB routing)")
    payloads = [
        {
            "query": "请简要介绍一下我们的产品A的主要功能。",
            "experimentId": RAG_EXPERIMENT_ID,
            "tenantId": "t1",
            "userId": "u1",
            "kbId": "kb_product",
            "scene": "qa",
            "queryCategory": "product_faq",
        },
        {
            "query": "帮我总结一下最近一版上线的核心改动。",
            "experimentId": RAG_EXPERIMENT_ID,
            "tenantId": "t1",
            "userId": "u2",
            "kbId": "kb_release_note",
            "scene": "qa",
            "queryCategory": "release_note",
        },
        {
            "query": "如果用户反馈搜索结果不相关，我们该如何排查？",
            "experimentId": RAG_EXPERIMENT_ID,
            "tenantId": "t2",
            "userId": "u3",
            "kbId": "kb_ops",
            "scene": "qa",
            "queryCategory": "how_to",
        },
    ]

    for i, body in enumerate(payloads, start=1):
        print(
            f"\n[RAG-1.{i}] chat request: userId={body.get('userId')}, "
            f"tenantId={body.get('tenantId')}, kbId={body.get('kbId')}"
        )
        r = requests.post(CHAT_BASE, json=body, timeout=15)
        _print_response(r)
        time.sleep(0.2)

    # ---------------- 调整实验阶段：模拟线上动态调权 ----------------

    print("\n[RAG-1.5] adjust traffic stage (stage 1: A=30, B=70)")
    r = requests.post(
        f"{ABTEST_BASE}/experiments/adjust-stage",
        json={
            "experimentId": RAG_EXPERIMENT_ID,
            "targetStageIndex": 1,
            "newWeights": {"A": 30, "B": 70},
        },
        timeout=10,
    )
    _print_response(r)

    print("\n[RAG-1.6] call /abtest/route directly after stage adjust")
    for uid, v in [
        ("u1", "tenant_id=t1&scene=qa&kb_id=kb_product&query_category=product_faq"),
        ("u2", "tenant_id=t1&scene=qa&kb_id=kb_release_note&query_category=release_note"),
        ("u3", "tenant_id=t2&scene=qa&kb_id=kb_ops&query_category=how_to"),
        ("u1", "tenant_id=t1&scene=qa&kb_id=kb_product&query_category=product_faq"),
    ]:
        r = requests.get(
            f"{ABTEST_BASE}/route",
            params={"experimentId": RAG_EXPERIMENT_ID, "userId": uid, "vars": v},
            timeout=10,
        )
        _print_response(r)
    # ---------------- 注入虚假数据：模拟更多 RAG 请求与 CSAT 评分 ----------------

    print("\n[RAG-2] inject fake metrics for REQUEST & CSAT (A/B)")
    fake_samples_per_version = 20
    for i in range(fake_samples_per_version):
        # 模拟每次请求都有 REQUEST=1.0
        for ver in ("A", "B"):
            requests.post(
                f"{ABTEST_BASE}/metrics/collect",
                json={
                    "experimentId": RAG_EXPERIMENT_ID,
                    "version": ver,
                    "metricName": "REQUEST",
                    "metricValue": 1.0,
                    "userId": f"fake_req_{ver.lower()}{i}",
                },
                timeout=10,
            )

        # 模拟 CSAT：A 稍低，B 稍高
        csat_a = 3.5 + random.uniform(-0.3, 0.3)
        csat_b = 4.2 + random.uniform(-0.3, 0.3)
        requests.post(
            f"{ABTEST_BASE}/metrics/collect",
            json={
                "experimentId": RAG_EXPERIMENT_ID,
                "version": "A",
                "metricName": "CSAT",
                "metricValue": csat_a,
                "userId": f"fake_csat_a{i}",
            },
            timeout=10,
        )
        requests.post(
            f"{ABTEST_BASE}/metrics/collect",
            json={
                "experimentId": RAG_EXPERIMENT_ID,
                "version": "B",
                "metricName": "CSAT",
                "metricValue": csat_b,
                "userId": f"fake_csat_b{i}",
            },
            timeout=10,
        )

    print("\n[RAG-3] run AB analysis for metric 'REQUEST' (continuous)")
    r = requests.post(
        f"{ABTEST_BASE}/analysis/run",
        json={
            "experimentId": RAG_EXPERIMENT_ID,
            "metricName": "REQUEST",
            "versionA": "A",
            "versionB": "B",
            "discrete": False,
        },
        timeout=15,
    )
    _print_response(r)

    print("\n[RAG-3.1] run AB analysis for metric 'REQUEST' (discrete)")
    r = requests.post(
        f"{ABTEST_BASE}/analysis/run",
        json={
            "experimentId": RAG_EXPERIMENT_ID,
            "metricName": "REQUEST",
            "versionA": "A",
            "versionB": "B",
            "discrete": True,
        },
        timeout=15,
    )
    _print_response(r)

    print("\n[RAG-4] run AB analysis for metric 'CSAT'")
    r = requests.post(
        f"{ABTEST_BASE}/analysis/run",
        json={
            "experimentId": RAG_EXPERIMENT_ID,
            "metricName": "CSAT",
            "versionA": "A",
            "versionB": "B",
            "discrete": False,
        },
        timeout=15,
    )
    _print_response(r)

    print("\n[RAG-5] monitor anomalies for metric 'REQUEST'")
    r = requests.get(
        f"{ABTEST_BASE}/monitor/anomalies",
        params={
            "experimentId": RAG_EXPERIMENT_ID,
            "metricName": "REQUEST",
            "windowSize": 20,
            "zThreshold": 2.0,
        },
        timeout=15,
    )
    _print_response(r)

    print("\n[RAG-5.1] monitor anomalies for metric 'CSAT'")
    r = requests.get(
        f"{ABTEST_BASE}/monitor/anomalies",
        params={
            "experimentId": RAG_EXPERIMENT_ID,
            "metricName": "CSAT",
            "windowSize": 20,
            "zThreshold": 2.0,
        },
        timeout=15,
    )
    _print_response(r)

    print("\n[RAG-6] generate report for RAG experiment (LLM will write final conclusion into DB if available)")
    r = requests.post(f"{ABTEST_BASE}/reports/{RAG_EXPERIMENT_ID}/generate", timeout=30)
    _print_response(r)

    print("\n[RAG-7] get report by id (this is what web UI will show)")
    r = requests.get(f"{ABTEST_BASE}/reports/{RAG_EXPERIMENT_ID}", timeout=15)
    _print_response(r)


def main() -> None:
    print("========== RAG + AB + LLM 实验链路 ==========")
    run_rag_ab_llm_experiment()
    print("\n[done] full_ab_rag_llm_smoke_test finished.")


if __name__ == "__main__":
    main()
