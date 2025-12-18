"""
搜索结果数据模型

定义 API 返回的搜索结果格式（使用 Pydantic 进行序列化和验证）
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchResultItem(BaseModel):
    """单个搜索结果项"""

    doc_id: str = Field(..., description="文档ID")
    score: float = Field(..., description="相关性分数")
    content: Optional[str] = Field(None, description="文档内容片段")
    highlight: Optional[str] = Field(None, description="高亮片段")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文档元数据")


class SearchResult(BaseModel):
    """
    搜索结果响应

    从 API 返回给客户端的完整结果
    """

    query: str = Field(..., description="原始查询")
    results: List[SearchResultItem] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="返回结果数量")
    took_ms: float = Field(..., description="耗时（毫秒）")

    # 调试信息（可选）
    recall_stats: Optional[Dict[str, Any]] = Field(
        None, description="召回统计信息（各路召回数量等）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "什么是 RAG？",
                "results": [
                    {
                        "doc_id": "doc_001",
                        "score": 0.95,
                        "content": "RAG（Retrieval-Augmented Generation）是一种...",
                        "highlight": None,
                        "metadata": {"filename": "rag_intro.pdf", "page": 1},
                    }
                ],
                "total": 1,
                "took_ms": 125.3,
                "recall_stats": {"vector": 100, "keyword": 100, "merged": 50},
            }
        }
