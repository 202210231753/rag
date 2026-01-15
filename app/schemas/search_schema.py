"""
搜索 API Schema

定义搜索请求和响应的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional

# 注意：SearchResult 和 SearchResultItem 已在 app/rag/models/search_result.py 中定义
# 这里只需要定义 SearchRequest


class SearchRequest(BaseModel):
    """多路召回搜索请求"""

    user_id: Optional[str] = Field(default=None, description="用户ID（用于历史与输入提示沉淀）")
    query: str = Field(..., min_length=1, description="搜索查询", example="什么是 RAG？")
    top_n: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    recall_top_k: int = Field(
        default=100, ge=10, le=500, description="召回阶段每路TopK"
    )
    enable_rerank: bool = Field(default=False, description="是否启用重排（暂不支持）")
    enable_ranking: bool = Field(default=True, description="是否启用排序引擎（黑名单、多样性、位置插入）")

    # 可选过滤条件（预留）
    filters: Optional[dict] = Field(default=None, description="过滤条件（暂未实现）")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "query": "如何使用多路召回提升检索效果？",
                "top_n": 5,
                "recall_top_k": 100,
                "enable_rerank": False,
                "enable_ranking": True,
            }
        }
