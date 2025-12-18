"""
搜索上下文数据模型

在整个召回流程中传递查询相关的上下文信息
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class SearchContext:
    """
    搜索上下文

    用于在向量化、分词、召回、融合等各个阶段传递查询信息
    """

    # 必填字段
    original_query: str  # 原始用户查询

    # 由服务生成的字段
    query_vector: Optional[List[float]] = None  # 查询向量（由 IEmbeddingService 生成）
    tokens: Optional[List[str]] = None  # 分词结果（由 ITokenizerService 生成）

    # 元数据（可选）
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """数据验证"""
        if not self.original_query or not self.original_query.strip():
            raise ValueError("original_query 不能为空")
