from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
	"""RAG 对话请求体。

	预留与 AB 实验强相关的字段：
	- experimentId: 可选，默认使用后端配置的实验 ID
	- tenantId / userId: 用户 & 租户信息，用于路由与分析
	- kbId: 知识库 ID，决定检索范围
	- scene: 使用场景（如 qa/chat/summarize），可作为 routing variable
	- queryCategory: 问题类型标签，便于更细的分流
	"""

	query: str = Field(..., description="用户问题文本")
	experiment_id: Optional[str] = Field(
		default=None,
		alias="experimentId",
		description="可选：指定使用的 AB 实验 ID，不传则使用默认 RAG 实验",
	)
	tenant_id: Optional[str] = Field(
		default=None,
		alias="tenantId",
		description="租户/业务线 ID，用于 AB 分流与报表分层",
	)
	user_id: Optional[str] = Field(
		default=None,
		alias="userId",
		description="用户 ID 或会话 ID，用于 sticky 分流",
	)
	kb_id: Optional[str] = Field(
		default=None,
		alias="kbId",
		description="知识库 ID，决定检索范围",
	)
	scene: Optional[str] = Field(
		default="qa",
		description="场景标签，例如 qa/chat/summarize/sql 等",
	)
	query_category: Optional[str] = Field(
		default=None,
		alias="queryCategory",
		description="问题类别标签，例如 product_faq/policy/how_to 等",
	)
	ext: Dict[str, Any] = Field(
		default_factory=dict,
		description="预留扩展字段，前端可传额外上下文信息",
	)


class ChatResponse(BaseModel):
	"""RAG 对话响应体。

	携带：
	- answer: 最终回复
	- version: 命中的 AB 版本（A/B/...）
	- experimentId: 所属 AB 实验 ID
	- debugInfo: 可选，返回一些内部调试信息（如使用的配置 key）
	"""

	answer: str = Field(..., description="回复内容")
	experiment_id: Optional[str] = Field(None, alias="experimentId")
	version: Optional[str] = Field(None, description="AB 实验分配到的版本，如 A/B")
	debug_info: Dict[str, Any] = Field(
		default_factory=dict,
		alias="debugInfo",
		description="调试信息，如使用的 RAG 配置 key、检索条数等",
	)

