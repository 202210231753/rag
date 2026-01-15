from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.abtest.hash_ring import ConsistentHashRing
from app.abtest.stats import mean, var, welch_t_test
from app.abtest.store import (
    Experiment,
    experiments,
    metrics,
    reports,
    rings_current,
    rings_previous,
    routes,
    seen_users,
)
from app.models.abtest import (
    ABTestAssignment,
    ABTestExperiment,
    ABTestMetric,
    ABTestReport,
    ABTestRoute,
    ABTestStage,
)


class ABTestService:
    """运营管理 - AB 实验服务（内存版）。

    目标：把 python_rag 的能力迁移到 rag 项目结构里。
    原则：仅新增/扩展，不破坏现有功能。
    """

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        observed_metrics: List[str],
        routing_variables: List[str],
        staged_weights: List[Dict[str, int]],
    ) -> Dict:
        if len(observed_metrics) < 2:
            raise HTTPException(status_code=400, detail="observedMetrics 至少需要 2 个指标")

        if self.db is not None:
            return self._create_experiment_db(
                experiment_id=experiment_id,
                name=name,
                observed_metrics=observed_metrics,
                routing_variables=routing_variables,
                staged_weights=staged_weights,
            )

        e = Experiment(
            experiment_id=experiment_id,
            name=name,
            observed_metrics=list(observed_metrics),
            routing_variables=list(routing_variables or []),
        )
        for w in staged_weights or []:
            e.stages.append(dict(w))
        experiments[experiment_id] = e
        return self._experiment_dict(e)

    def start_experiment(self, experiment_id: str) -> Dict:
        if self.db is not None:
            return self._start_experiment_db(experiment_id)

        e = experiments.get(experiment_id)
        if not e:
            raise HTTPException(status_code=404, detail="experiment not found")
        if not e.stages:
            raise HTTPException(status_code=400, detail="no stages configured")
        w = e.stages[0]
        self._cache_ring(experiment_id, w, as_current=True, keep_previous=True)
        e.status = "STARTED"
        e.started_at = datetime.utcnow().isoformat()
        return self._experiment_dict(e)

    def adjust_stage(
        self,
        experiment_id: str,
        target_stage_index: int,
        new_weights: Dict[str, int],
    ) -> Dict:
        if self.db is not None:
            return self._adjust_stage_db(experiment_id, target_stage_index, new_weights)

        e = experiments.get(experiment_id)
        if not e:
            raise HTTPException(status_code=404, detail="experiment not found")

        e.stages.append(dict(new_weights))
        self._cache_ring(experiment_id, new_weights, as_current=True, keep_previous=True)
        return {
            "stageIndex": target_stage_index,
            "versionWeights": dict(new_weights),
        }

    def route(self, experiment_id: str, user_id: str, vars_str: str = "") -> Dict:
        if self.db is not None:
            return self._route_db(experiment_id, user_id, vars_str)

        version = self._route_with_vars(experiment_id, user_id, vars_str)
        rec = {
            "experimentId": experiment_id,
            "userId": user_id,
            "version": version,
            "vars": vars_str or "",
            "routedAt": datetime.utcnow().isoformat(),
        }
        routes.append(rec)
        return rec

    def collect_metric(
        self,
        experiment_id: str,
        version: str,
        metric_name: str,
        metric_value: float,
        user_id: Optional[str] = None,
    ) -> Dict:
        if self.db is not None:
            return self._collect_metric_db(experiment_id, version, metric_name, metric_value, user_id)

        rec = {
            "experimentId": experiment_id,
            "version": version,
            "metricName": metric_name,
            "metricValue": float(metric_value),
            "userId": user_id,
            "collectedAt": datetime.utcnow().isoformat(),
        }
        metrics.append(rec)
        return rec

    def run_analysis(
        self,
        experiment_id: str,
        metric_name: str,
        version_a: str = "A",
        version_b: str = "B",
        discrete: bool = False,
    ) -> Dict:
        if discrete:
            raise HTTPException(status_code=400, detail="chi_square not implemented")

        if self.db is not None:
            return self._run_analysis_db(experiment_id, metric_name, version_a, version_b)

        a = [
            m["metricValue"]
            for m in metrics
            if m["experimentId"] == experiment_id
            and m["metricName"] == metric_name
            and m["version"] == version_a
        ]
        b = [
            m["metricValue"]
            for m in metrics
            if m["experimentId"] == experiment_id
            and m["metricName"] == metric_name
            and m["version"] == version_b
        ]
        ma, mb = mean(a), mean(b)
        p = welch_t_test(a, b)
        uplift = (mb - ma) / max(abs(ma), 1e-9)
        return {
            "experimentId": experiment_id,
            "metricName": metric_name,
            "testType": "t_test",
            "pvalue": p,
            "uplift": uplift,
        }

    def monitor_anomalies(
        self,
        experiment_id: str,
        metric_name: str,
        window_size: int = 50,
        z_threshold: float = 3.0,
    ) -> List[Dict]:
        """简易异常监控：对每个版本计算(最近窗口均值 - 全量均值)/std。"""

        if self.db is not None:
            return self._monitor_anomalies_db(experiment_id, metric_name, window_size, z_threshold)

        by_version: Dict[str, List[float]] = defaultdict(list)
        for m in metrics:
            if m["experimentId"] != experiment_id or m["metricName"] != metric_name:
                continue
            by_version[m["version"]].append(float(m["metricValue"]))

        out: List[Dict] = []
        for version, xs in by_version.items():
            if not xs:
                continue
            baseline_mean = mean(xs)
            baseline_var = var(xs)
            baseline_std = math.sqrt(baseline_var) if baseline_var == baseline_var else float("nan")

            window = xs[-max(1, window_size) :]
            window_mean = mean(window)
            if not baseline_std or baseline_std != baseline_std:
                z = 0.0
            else:
                z = (window_mean - baseline_mean) / baseline_std

            out.append(
                {
                    "version": version,
                    "metricName": metric_name,
                    "windowMean": window_mean,
                    "baselineMean": baseline_mean,
                    "zscore": z,
                    "isAnomaly": abs(z) >= z_threshold,
                }
            )
        return out

    def generate_report(self, experiment_id: str) -> Dict:
        if self.db is not None:
            return self._generate_report_db(experiment_id)

        e = experiments.get(experiment_id)
        if not e:
            raise HTTPException(status_code=404, detail="experiment not found")

        design = self._build_design_section(e)
        execution = self._build_execution_section(e)
        analysis = self._build_analysis_section(e)
        conclusion = self._build_conclusion_section(e)

        # 使用大模型生成一份“终版实验报告”（可选）
        llm_final = _call_llm_final_report(experiment_id, design, execution, analysis, conclusion)

        rep = {
            "experimentId": experiment_id,
            "designAndHypothesis": design,
            "executionAndKeyData": execution,
            "analysisAndStatistics": analysis,
            "conclusionsAndRecommendations": conclusion,
        }
        if llm_final:
            rep["llmFinalReport"] = llm_final
        reports[experiment_id] = rep
        return rep

    def get_report(self, experiment_id: str) -> Optional[Dict]:
        if self.db is not None:
            rep_row = self.db.execute(
                select(ABTestReport).where(ABTestReport.experiment_id == experiment_id)
            ).scalar_one_or_none()
            if not rep_row:
                return None
            base = {
                "experimentId": rep_row.experiment_id,
                "designAndHypothesis": rep_row.design_and_hypothesis,
                "executionAndKeyData": rep_row.execution_and_key_data,
                "analysisAndStatistics": rep_row.analysis_and_statistics,
                "conclusionsAndRecommendations": rep_row.conclusions_and_recommendations,
            }
            # 若存在持久化的 LLM 终版报告，则一并返回，供前端直接展示
            if getattr(rep_row, "llm_final_report", None):
                base["llmFinalReport"] = rep_row.llm_final_report
            return base
        return reports.get(experiment_id)

    # ----------------- DB implementations -----------------

    def _create_experiment_db(
        self,
        experiment_id: str,
        name: str,
        observed_metrics: List[str],
        routing_variables: List[str],
        staged_weights: List[Dict[str, int]],
    ) -> Dict:
        assert self.db is not None

        exists = self.db.execute(
            select(ABTestExperiment).where(ABTestExperiment.experiment_id == experiment_id)
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="experiment already exists")

        exp = ABTestExperiment(
            experiment_id=experiment_id,
            name=name,
            observed_metrics=list(observed_metrics),
            routing_variables=list(routing_variables or []),
            status="CONFIGURED",
            started_at=None,
        )
        self.db.add(exp)

        stages_out: List[Dict[str, int]] = []
        for idx, w in enumerate(staged_weights or []):
            stage = ABTestStage(experiment_id=experiment_id, stage_index=idx, weights=dict(w))
            self.db.add(stage)
            stages_out.append(dict(w))

        self.db.commit()
        return {
            "experimentId": experiment_id,
            "name": name,
            "observedMetrics": list(observed_metrics),
            "routingVariables": list(routing_variables or []),
            "stages": stages_out,
            "status": "CONFIGURED",
            "startedAt": None,
        }

    def _start_experiment_db(self, experiment_id: str) -> Dict:
        assert self.db is not None

        exp = self.db.execute(
            select(ABTestExperiment).where(ABTestExperiment.experiment_id == experiment_id)
        ).scalar_one_or_none()
        if not exp:
            raise HTTPException(status_code=404, detail="experiment not found")

        stage0 = self.db.execute(
            select(ABTestStage)
            .where(ABTestStage.experiment_id == experiment_id)
            .where(ABTestStage.stage_index == 0)
        ).scalar_one_or_none()
        if not stage0:
            raise HTTPException(status_code=400, detail="no stages configured")

        exp.status = "STARTED"
        exp.started_at = datetime.utcnow()
        self.db.commit()

        stages = (
            self.db.execute(
                select(ABTestStage)
                .where(ABTestStage.experiment_id == experiment_id)
                .order_by(ABTestStage.stage_index.asc())
            )
            .scalars()
            .all()
        )

        return {
            "experimentId": exp.experiment_id,
            "name": exp.name,
            "observedMetrics": list(exp.observed_metrics or []),
            "routingVariables": list(exp.routing_variables or []),
            "stages": [dict(s.weights or {}) for s in stages],
            "status": exp.status,
            "startedAt": exp.started_at.isoformat() if exp.started_at else None,
        }

    def _adjust_stage_db(
        self, experiment_id: str, target_stage_index: int, new_weights: Dict[str, int]
    ) -> Dict:
        assert self.db is not None

        exp = self.db.execute(
            select(ABTestExperiment).where(ABTestExperiment.experiment_id == experiment_id)
        ).scalar_one_or_none()
        if not exp:
            raise HTTPException(status_code=404, detail="experiment not found")

        max_idx = self.db.execute(
            select(func.max(ABTestStage.stage_index)).where(ABTestStage.experiment_id == experiment_id)
        ).scalar_one()
        next_idx = int(max_idx + 1) if max_idx is not None else 0

        stage = ABTestStage(experiment_id=experiment_id, stage_index=next_idx, weights=dict(new_weights))
        self.db.add(stage)
        self.db.commit()

        return {"stageIndex": target_stage_index, "versionWeights": dict(new_weights)}

    def _route_db(self, experiment_id: str, user_id: str, vars_str: str) -> Dict:
        assert self.db is not None

        exp = self.db.execute(
            select(ABTestExperiment).where(ABTestExperiment.experiment_id == experiment_id)
        ).scalar_one_or_none()
        if not exp:
            raise HTTPException(status_code=404, detail="experiment not found")

        # sticky assignment：先查历史分配
        assign = self.db.execute(
            select(ABTestAssignment)
            .where(ABTestAssignment.experiment_id == experiment_id)
            .where(ABTestAssignment.user_id == user_id)
            .where(ABTestAssignment.vars == (vars_str or ""))
        ).scalar_one_or_none()

        if assign:
            version = assign.version
        else:
            latest_stage = self.db.execute(
                select(ABTestStage)
                .where(ABTestStage.experiment_id == experiment_id)
                .order_by(ABTestStage.stage_index.desc())
                .limit(1)
            ).scalar_one_or_none()
            if not latest_stage:
                version = "control"
                stage_index = 0
            else:
                weights = dict(latest_stage.weights or {})
                stage_index = int(latest_stage.stage_index)
                comp = f"{experiment_id}:{user_id}:{vars_str or ''}"
                ring = ConsistentHashRing(weights, 100)
                version = ring.route(comp) or "control"

            assign = ABTestAssignment(
                experiment_id=experiment_id,
                user_id=user_id,
                vars=(vars_str or ""),
                version=version,
                stage_index=stage_index,
            )
            self.db.add(assign)

        route = ABTestRoute(
            experiment_id=experiment_id,
            user_id=user_id,
            vars=(vars_str or ""),
            version=version,
        )
        self.db.add(route)
        self.db.commit()

        return {
            "experimentId": experiment_id,
            "userId": user_id,
            "version": version,
            "vars": vars_str or "",
            "routedAt": route.routed_at.isoformat(),
        }

    def _collect_metric_db(
        self,
        experiment_id: str,
        version: str,
        metric_name: str,
        metric_value: float,
        user_id: Optional[str],
    ) -> Dict:
        assert self.db is not None

        rec = ABTestMetric(
            experiment_id=experiment_id,
            version=version,
            metric_name=metric_name,
            metric_value=float(metric_value),
            user_id=user_id,
        )
        self.db.add(rec)
        self.db.commit()
        return {
            "experimentId": experiment_id,
            "version": version,
            "metricName": metric_name,
            "metricValue": float(metric_value),
            "userId": user_id,
            "collectedAt": rec.collected_at.isoformat(),
        }

    def _run_analysis_db(
        self, experiment_id: str, metric_name: str, version_a: str, version_b: str
    ) -> Dict:
        assert self.db is not None

        a = (
            self.db.execute(
                select(ABTestMetric.metric_value)
                .where(ABTestMetric.experiment_id == experiment_id)
                .where(ABTestMetric.metric_name == metric_name)
                .where(ABTestMetric.version == version_a)
            )
            .scalars()
            .all()
        )
        b = (
            self.db.execute(
                select(ABTestMetric.metric_value)
                .where(ABTestMetric.experiment_id == experiment_id)
                .where(ABTestMetric.metric_name == metric_name)
                .where(ABTestMetric.version == version_b)
            )
            .scalars()
            .all()
        )

        ma, mb = mean([float(x) for x in a]), mean([float(x) for x in b])
        p = welch_t_test([float(x) for x in a], [float(x) for x in b])
        uplift = (mb - ma) / max(abs(ma), 1e-9)
        return {
            "experimentId": experiment_id,
            "metricName": metric_name,
            "testType": "t_test",
            "pvalue": p,
            "uplift": uplift,
        }

    def _monitor_anomalies_db(
        self, experiment_id: str, metric_name: str, window_size: int, z_threshold: float
    ) -> List[Dict]:
        assert self.db is not None

        rows = self.db.execute(
            select(ABTestMetric.version, ABTestMetric.metric_value)
            .where(ABTestMetric.experiment_id == experiment_id)
            .where(ABTestMetric.metric_name == metric_name)
            .order_by(ABTestMetric.id.asc())
        ).all()

        by_version: Dict[str, List[float]] = defaultdict(list)
        for version, value in rows:
            by_version[str(version)].append(float(value))

        out: List[Dict] = []
        for version, xs in by_version.items():
            if not xs:
                continue
            baseline_mean = mean(xs)
            baseline_var = var(xs)
            baseline_std = math.sqrt(baseline_var) if baseline_var == baseline_var else float("nan")

            window = xs[-max(1, int(window_size)) :]
            window_mean = mean(window)
            if not baseline_std or baseline_std != baseline_std:
                z = 0.0
            else:
                z = (window_mean - baseline_mean) / baseline_std

            out.append(
                {
                    "version": version,
                    "metricName": metric_name,
                    "windowMean": window_mean,
                    "baselineMean": baseline_mean,
                    "zscore": z,
                    "isAnomaly": abs(z) >= float(z_threshold),
                }
            )
        return out

    def _generate_report_db(self, experiment_id: str) -> Dict:
        assert self.db is not None

        exp = self.db.execute(
            select(ABTestExperiment).where(ABTestExperiment.experiment_id == experiment_id)
        ).scalar_one_or_none()
        if not exp:
            raise HTTPException(status_code=404, detail="experiment not found")

        stages = (
            self.db.execute(
                select(ABTestStage)
                .where(ABTestStage.experiment_id == experiment_id)
                .order_by(ABTestStage.stage_index.asc())
            )
            .scalars()
            .all()
        )

        # 复用原内存版的 report 构造逻辑：把 DB 实验映射成临时 Experiment
        temp = Experiment(
            experiment_id=exp.experiment_id,
            name=exp.name,
            observed_metrics=list(exp.observed_metrics or []),
            routing_variables=list(exp.routing_variables or []),
            stages=[dict(s.weights or {}) for s in stages],
            status=exp.status,
            started_at=exp.started_at.isoformat() if exp.started_at else None,
        )

        # 临时计算 execution 数据（DB 版）
        design = self._build_design_section(temp)
        execution = self._build_execution_section_db(temp)
        analysis = self._build_analysis_section_db(temp)
        conclusion = self._build_conclusion_section_db(temp)

        # 先尝试调用大模型生成终版结论；若失败则回退到规则版结论
        llm_final = _call_llm_final_report(experiment_id, design, execution, analysis, conclusion)
        conclusion_to_save = llm_final or conclusion

        rep = self.db.execute(
            select(ABTestReport).where(ABTestReport.experiment_id == experiment_id)
        ).scalar_one_or_none()

        if rep is None:
            rep = ABTestReport(
                experiment_id=experiment_id,
                design_and_hypothesis=design,
                execution_and_key_data=execution,
                analysis_and_statistics=analysis,
                conclusions_and_recommendations=conclusion_to_save,
                llm_final_report=llm_final,
            )
            self.db.add(rep)
        else:
            rep.design_and_hypothesis = design
            rep.execution_and_key_data = execution
            rep.analysis_and_statistics = analysis
            rep.conclusions_and_recommendations = conclusion_to_save
            rep.llm_final_report = llm_final

        self.db.commit()
        out = {
            "experimentId": experiment_id,
            "designAndHypothesis": design,
            "executionAndKeyData": execution,
            "analysisAndStatistics": analysis,
            "conclusionsAndRecommendations": conclusion_to_save,
        }
        if llm_final:
            out["llmFinalReport"] = llm_final
        return out

    def _build_execution_section_db(self, e: Experiment) -> str:
        assert self.db is not None

        route_rows = self.db.execute(
            select(ABTestRoute.version, func.count(ABTestRoute.id))
            .where(ABTestRoute.experiment_id == e.experiment_id)
            .group_by(ABTestRoute.version)
        ).all()
        cnt_by_v = {str(v): int(c) for v, c in route_rows}

        metric_rows = self.db.execute(
            select(ABTestMetric.metric_name, ABTestMetric.version, func.count(ABTestMetric.id))
            .where(ABTestMetric.experiment_id == e.experiment_id)
            .group_by(ABTestMetric.metric_name, ABTestMetric.version)
        ).all()
        metric_cnt: Dict[str, Dict[str, int]] = defaultdict(dict)
        for mn, ver, c in metric_rows:
            metric_cnt[str(mn)][str(ver)] = int(c)

        lines = [
            "实验执行与关键数据",
            f"- 状态：{e.status}",
            f"- 开始时间：{e.started_at}",
            f"- 路由请求量：{cnt_by_v}",
        ]
        for mn, vv in metric_cnt.items():
            lines.append(f"- 指标采集量 {mn}：{vv}")
        return "\n".join(lines) + "\n"

    def _build_analysis_section_db(self, e: Experiment) -> str:
        a, b = self._pick_two_versions(e)
        chunks: List[str] = ["结果分析与统计"]
        for mn in e.observed_metrics:
            res = self._run_analysis_db(e.experiment_id, mn, a, b)
            chunks.append(
                f"- {mn}: test=t_test, uplift={res['uplift']:.6f}, pvalue={res['pvalue']:.6f} (A={a}, B={b})"
            )
        return "\n".join(chunks) + "\n"

    def _build_conclusion_section_db(self, e: Experiment) -> str:
        a, b = self._pick_two_versions(e)
        wins = 0
        total = 0
        for mn in e.observed_metrics:
            res = self._run_analysis_db(e.experiment_id, mn, a, b)
            total += 1
            if res["pvalue"] == res["pvalue"] and res["pvalue"] < 0.05 and res["uplift"] > 0:
                wins += 1

        if total == 0:
            return "结论与建议\n- 暂无可用指标数据，建议先采集数据再分析。\n"

        if wins >= max(1, total // 2):
            return (
                "结论与建议\n"
                f"- 版本 {b} 在多数指标上显著优于 {a}，建议逐步扩大 {b} 的流量占比。\n"
                "- 扩量时建议开启异常监控（z-score），观察跳出率/停留时长等防护指标。\n"
            )

        return (
            "结论与建议\n"
            f"- 目前未观察到版本 {b} 相对 {a} 的稳定显著提升，建议继续采样或调整实验设计。\n"
            "- 可考虑按分流变量做分层分析，避免总体被人群结构稀释。\n"
        )

    # ----------------- internal helpers -----------------

    def _cache_ring(
        self,
        experiment_id: str,
        weights: Dict[str, int],
        as_current: bool,
        keep_previous: bool,
    ) -> None:
        if keep_previous and experiment_id in rings_current:
            rings_previous[experiment_id] = rings_current[experiment_id]
        if as_current:
            rings_current[experiment_id] = {"weights": dict(weights), "vnodes": 100}

    def _route_with_vars(self, experiment_id: str, user_id: str, vars_str: str) -> str:
        seen_key = f"seen:{experiment_id}"
        s = seen_users.setdefault(seen_key, set())
        comp = f"{experiment_id}:{user_id}:{vars_str or ''}"

        # 老用户：尽可能保持上一阶段桶位
        if user_id in s and experiment_id in rings_previous:
            prev = rings_previous[experiment_id]
            rprev = ConsistentHashRing(prev["weights"], prev["vnodes"])
            return rprev.route(comp) or "control"

        cur = rings_current.get(experiment_id)
        if not cur:
            return "control"

        rcur = ConsistentHashRing(cur["weights"], cur["vnodes"])
        v = rcur.route(comp) or "control"
        s.add(user_id)
        return v

    def _experiment_dict(self, e: Experiment) -> Dict:
        return {
            "experimentId": e.experiment_id,
            "name": e.name,
            "observedMetrics": list(e.observed_metrics),
            "routingVariables": list(e.routing_variables),
            "stages": [dict(s) for s in e.stages],
            "status": e.status,
            "startedAt": e.started_at,
        }

    def _pick_two_versions(self, e: Experiment) -> Tuple[str, str]:
        if e.stages and e.stages[0]:
            keys = list(e.stages[0].keys())
            if len(keys) >= 2:
                return keys[0], keys[1]
        return "A", "B"

    def _build_design_section(self, e: Experiment) -> str:
        a, b = self._pick_two_versions(e)
        metrics_text = "、".join(e.observed_metrics)
        vars_text = "、".join(e.routing_variables) if e.routing_variables else "(无)"
        stage0 = e.stages[0] if e.stages else {}
        return (
            "实验设计与假设\n"
            f"- 实验ID：{e.experiment_id}\n"
            f"- 实验名称：{e.name}\n"
            f"- 观测指标：{metrics_text}\n"
            f"- 分流变量：{vars_text}\n"
            f"- 初始流量权重：{stage0}\n"
            f"- 假设：版本 {b} 在关键指标上优于版本 {a}。\n"
        )

    def _build_execution_section(self, e: Experiment) -> str:
        # 路由样本数
        cnt_by_v: Dict[str, int] = defaultdict(int)
        for r in routes:
            if r["experimentId"] == e.experiment_id:
                cnt_by_v[r["version"]] += 1

        # 指标样本数
        metric_cnt: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for m in metrics:
            if m["experimentId"] != e.experiment_id:
                continue
            metric_cnt[m["metricName"]][m["version"]] += 1

        lines = [
            "实验执行与关键数据",
            f"- 状态：{e.status}",
            f"- 开始时间：{e.started_at}",
            f"- 路由用户量(粗略)：{dict(cnt_by_v)}",
        ]
        for mn, vv in metric_cnt.items():
            lines.append(f"- 指标采集量 {mn}：{dict(vv)}")
        return "\n".join(lines) + "\n"

    def _build_analysis_section(self, e: Experiment) -> str:
        a, b = self._pick_two_versions(e)
        chunks: List[str] = ["结果分析与统计"]
        for mn in e.observed_metrics:
            res = self.run_analysis(e.experiment_id, mn, a, b, discrete=False)
            chunks.append(
                f"- {mn}: test=t_test, uplift={res['uplift']:.6f}, pvalue={res['pvalue']:.6f} (A={a}, B={b})"
            )
        return "\n".join(chunks) + "\n"

    def _build_conclusion_section(self, e: Experiment) -> str:
        a, b = self._pick_two_versions(e)
        wins = 0
        total = 0
        for mn in e.observed_metrics:
            res = self.run_analysis(e.experiment_id, mn, a, b, discrete=False)
            total += 1
            if res["pvalue"] == res["pvalue"] and res["pvalue"] < 0.05 and res["uplift"] > 0:
                wins += 1

        if total == 0:
            return "结论与建议\n- 暂无可用指标数据，建议先采集数据再分析。\n"

        if wins >= max(1, total // 2):
            return (
                "结论与建议\n"
                f"- 版本 {b} 在多数指标上显著优于 {a}，建议逐步扩大 {b} 的流量占比。\n"
                "- 扩量时建议开启异常监控（z-score），观察跳出率/停留时长等防护指标。\n"
            )

        return (
            "结论与建议\n"
            f"- 目前未观察到版本 {b} 相对 {a} 的稳定显著提升，建议继续采样或调整实验设计。\n"
            "- 可考虑按分流变量做分层分析，避免总体被人群结构稀释。\n"
        )


def _call_llm_final_report(
    experiment_id: str,
    design: str,
    execution: str,
    analysis: str,
    conclusion: str,
) -> Optional[str]:
    """调用 Qwen3-4B 生成终版实验报告（快速失败，不阻塞主链路）。

    - 默认走本地 vLLM OpenAI 兼容服务：http://127.0.0.1:8000/v1
    - 可通过环境变量覆盖：
        - QWEN_API_BASE (默认 http://127.0.0.1:8000/v1)
        - QWEN_API_MODEL (默认 Qwen3-4B-Instruct-2507)
        - QWEN_API_KEY  (可选，若 vLLM 开启了鉴权)
        - QWEN_TIMEOUT_SECONDS (默认 3 秒，用于 requests 超时)

    出错或超时时返回 None，不影响主流程。
    """

    import json

    base = os.getenv("QWEN_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")
    model = os.getenv("QWEN_API_MODEL", "Qwen3-4B-Instruct-2507")
    api_key = os.getenv("QWEN_API_KEY", "")
    try:
        timeout_sec = float(os.getenv("QWEN_TIMEOUT_SECONDS", "30"))
    except ValueError:
        timeout_sec = 3.0

    url = f"{base}/chat/completions"

    system_prompt = "你是一名经验丰富的互联网 A/B 实验分析专家，擅长为业务方撰写简洁专业的中文实验报告。"

    user_prompt = f"""请根据下面这份 A/B 实验的原始报告草稿，为业务方生成一份结构化的终版实验总结报告（中文）：

[实验设计与假设]
{design}

[实验执行与关键数据]
{execution}

[结果分析与统计]
{analysis}

[原始结论与建议]
{conclusion}

要求：
1. 按“实验背景与目标 / 实验配置 / 关键结果 / 风险与限制 / 结论与上线建议”这五个小节组织内容；
2. 用通俗的业务语言解释 uplift、p 值等统计结果的含义，不需要给出公式；
3. 明确说明当前是否建议扩大流量或全量上线，并给出下一步行动建议；
4. 不要逐字照抄原始草稿，而是做归纳和润色；
5. 只输出终版报告正文，无需再次分段复述输入内容。"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        import requests  # 局部导入，避免在极简环境下强依赖

        # 使用较短超时时间，避免在 Qwen 未启动时阻塞 /reports 接口过久
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if not isinstance(content, str):
            return None
        return content.strip()
    except Exception:
        # 出错时静默失败，让接口依然返回规则版报告
        return None


import math  # 放在底部避免打断主体逻辑
