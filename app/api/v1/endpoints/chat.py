from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.schemas.stats_schema import ApiResponse
from app.services.rag_service import RAGService


router = APIRouter()


@router.post("", response_model=ApiResponse[ChatResponse])
def chat(
	req: ChatRequest,
	db: Session = Depends(deps.get_db),
) -> ApiResponse[ChatResponse]:
	"""RAG 对话入口，并接入 AB 实验分流。

	实际 URL 为：POST /api/v1/chat

	- 根据 tenantId/userId/kbId/scene/queryCategory 等信息做 AB 路由；
	- 当前返回占位回答，主要用于验证“RAG + AB 实验”链路；
	- 后续可以在 RAGService 内部接入真正的向量检索和大模型调用。
	"""

	service = RAGService(db)
	data = service.chat(req)
	return ApiResponse(data=data)

