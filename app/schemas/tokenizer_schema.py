from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Operation = Literal["ADD", "DELETE"]


class TokenizerSelectRequest(BaseModel):
    tokenizer_id: str = Field(..., alias="tokenizerId", description="分词器唯一标识ID")

    model_config = ConfigDict(populate_by_name=True)


class TermUpsertRequest(BaseModel):
    term: str = Field(..., description="目标词条")
    operation: Operation = Field(..., description="操作类型：ADD(新增), DELETE(删除)")

    model_config = ConfigDict(populate_by_name=True)


class SuccessResponse(BaseModel):
    success: bool = True


class BatchResultResponse(BaseModel):
    success_count: int = Field(..., alias="successCount", description="成功处理条数")
    fail_count: int = Field(..., alias="failCount", description="失败条数")

    model_config = ConfigDict(populate_by_name=True)


class TokenizeRequest(BaseModel):
    text: str = Field(..., description="待分词文本")


class TokenizeResponse(BaseModel):
    tokenizer_id: str = Field(..., alias="tokenizerId", description="当前生效的分词器ID")
    tokens: list[str] = Field(..., description="分词结果")

    model_config = ConfigDict(populate_by_name=True)
