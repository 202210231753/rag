from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.abtest_service import ABTestService


DEFAULT_RAG_EXPERIMENT_ID = "rag_chat_prompt_v1"


class RAGService:
	"""RAG 对话服务（已接入 AB 实验）。

	当前版本主要做两件事：
	1. 调用 AB 实验路由，为每次对话分配版本（A/B/...）。
	2. 预留 RAG pipeline 的入口，后续可按版本切换不同配置。

	这里先用占位实现：不真正连向量库和大模型，只返回一个带有版本信息的答复，
	方便验证“RAG + AB 实验”的调用链是否跑通。
	"""

	def __init__(self, db: Optional[Session] = None) -> None:
		self.db = db
		self.ab_service = ABTestService(db)

	def _build_routing_vars_str(self, req: ChatRequest) -> str:
		"""把和 RAG 相关的维度编码成 AB 路由变量串。

		示例结果："tenant_id=t1&scene=qa&kb_id=kb1&query_category=product_faq"
		"""

		parts = []
		if req.tenant_id:
			parts.append(f"tenant_id={req.tenant_id}")
		if req.scene:
			parts.append(f"scene={req.scene}")
		if req.kb_id:
			parts.append(f"kb_id={req.kb_id}")
		if req.query_category:
			parts.append(f"query_category={req.query_category}")
		return "&".join(parts)

	def chat(self, req: ChatRequest) -> ChatResponse:
		"""执行一次 RAG 对话，并接入 AB 实验分流。"""

		experiment_id = req.experiment_id or DEFAULT_RAG_EXPERIMENT_ID
		user_id = req.user_id or "anonymous"

		vars_str = self._build_routing_vars_str(req)

		route_res: Dict[str, Any] = self.ab_service.route(
			experiment_id=experiment_id,
			user_id=user_id,
			vars_str=vars_str,
		)
		version = route_res.get("version", "control")

		# TODO：此处接入真正的 RAG pipeline（按 version 切不同配置）
		rag_config_key = f"{experiment_id}:{version}"
		answer = (
			f"【占位回复】已命中 AB 实验 {experiment_id} 的版本 {version}。"
			f"（config={rag_config_key}）\n\n你问的是：{req.query}"
		)

		# 简单示例：把每个请求计为一个指标，用于观察 A/B 请求量与基础效果
		try:
			self.ab_service.collect_metric(
				experiment_id=experiment_id,
				version=version,
				metric_name="REQUEST",
				metric_value=1.0,
				user_id=user_id,
			)
		except Exception:
			# 指标上报失败不影响主流程
			pass

		debug_info: Dict[str, Any] = {
			"routingVars": vars_str,
			"ragConfigKey": rag_config_key,
		}

		return ChatResponse(
			answer=answer,
			experiment_id=experiment_id,
			version=version,
			debug_info=debug_info,
		)

