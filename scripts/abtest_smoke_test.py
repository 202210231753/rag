"""AB 实验 + 实验报告 smoke test。

1) 先确保 MySQL 可连 & 已建表：
   /home/yl/yl/jzz/conda/envs/all-in-rag/bin/python -m app.abtest.init_db

2) 再启动服务：
   /home/yl/yl/jzz/conda/envs/all-in-rag/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

3) 运行本脚本：
   /home/yl/yl/jzz/conda/envs/all-in-rag/bin/python scripts/abtest_smoke_test.py
"""

from __future__ import annotations

import json
import time

import requests


BASE = "http://127.0.0.1:8001/api/v1/abtest"


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


def main() -> None:
    exp_id = f"exp_smoke_{int(time.time())}"

    print(f"\n[1] create experiment, exp_id={exp_id}")
    r = requests.post(
        f"{BASE}/experiments",
        json={
            "experimentId": exp_id,
            "name": "搜索排序AB(smoke)",
            "observedMetrics": ["CTR", "QV"],
            "routingVariables": ["gender", "city"],
            "stagedWeights": [{"A": 50, "B": 50}],
        },
        timeout=10,
    )
    _print_response(r)

    print("\n[2] start experiment")
    r = requests.post(f"{BASE}/experiments/{exp_id}/start", timeout=10)
    _print_response(r)

    print("\n[3] route some users (stage 0)")
    for uid, v in [("u1", "gender=M&city=sh"), ("u2", "gender=F&city=bj"), ("u1", "gender=M&city=sh")]:
        r = requests.get(f"{BASE}/route", params={"experimentId": exp_id, "userId": uid, "vars": v}, timeout=10)
        _print_response(r)

    print("\n[3.5] adjust stage (add stage 1: A=20, B=80)")
    r = requests.post(
        f"{BASE}/experiments/adjust-stage",
        json={
            "experimentId": exp_id,
            "targetStageIndex": 1,
            "newWeights": {"A": 20, "B": 80},
        },
        timeout=10,
    )
    _print_response(r)

    print("\n[3.6] route some users after adjust-stage (stage 1)")
    for uid, v in [
        ("u1", "gender=M&city=sh"),
        ("u2", "gender=F&city=bj"),
        ("u3", "gender=M&city=hz"),
        ("u4", "gender=F&city=cd"),
    ]:
        r = requests.get(f"{BASE}/route", params={"experimentId": exp_id, "userId": uid, "vars": v}, timeout=10)
        _print_response(r)

    print("\n[4] collect metrics")
    # 给 A/B 填一些样本，确保 t-test 有意义
    for i in range(10):
        requests.post(
            f"{BASE}/metrics/collect",
            json={
                "experimentId": exp_id,
                "version": "A",
                "metricName": "CTR",
                "metricValue": 0.10,
                "userId": f"ua{i}",
            },
            timeout=10,
        )
        requests.post(
            f"{BASE}/metrics/collect",
            json={
                "experimentId": exp_id,
                "version": "B",
                "metricName": "CTR",
                "metricValue": 0.16,
                "userId": f"ub{i}",
            },
            timeout=10,
        )

    print("\n[5] run analysis")
    r = requests.post(
        f"{BASE}/analysis/run",
        json={"experimentId": exp_id, "metricName": "CTR", "versionA": "A", "versionB": "B", "discrete": False},
        timeout=10,
    )
    _print_response(r)

    print("\n[6] monitor anomalies")
    r = requests.get(
        f"{BASE}/monitor/anomalies",
        params={"experimentId": exp_id, "metricName": "CTR", "windowSize": 20, "zThreshold": 2.0},
        timeout=10,
    )
    _print_response(r)

    print("\n[7] generate report")
    r = requests.post(f"{BASE}/reports/{exp_id}/generate", timeout=10)
    _print_response(r)

    print("\n[8] get report by id (for web viewing)")
    r = requests.get(f"{BASE}/reports/{exp_id}", timeout=10)
    _print_response(r)

    print("\n[done]")


if __name__ == "__main__":
    main()
