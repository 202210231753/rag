"""
推荐系统的请求和响应 Schema
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============= 内容推荐相关 Schema =============

class ContentRecommendRequest(BaseModel):
    """内容推荐请求"""
    user_id: str = Field(..., description="用户ID", example="user_123")
    trace_id: Optional[str] = Field(None, description="追踪ID，用于日志追踪", example="trace_abc_123")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "trace_id": "trace_abc_123"
            }
        }


class ItemResponse(BaseModel):
    """推荐项基本信息"""
    item_id: str = Field(..., description="内容ID")
    content: str = Field(..., description="内容文本")
    tags: List[str] = Field(default_factory=list, description="内容标签")
    score: float = Field(0.0, description="推荐分数")
    strategy_source: str = Field("algorithm", description="推荐来源: algorithm/hot/curated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "item_001",
                "content": "如何使用 FastAPI 构建 RESTful API",
                "tags": ["编程", "Python", "Web开发"],
                "score": 0.95,
                "strategy_source": "algorithm"
            }
        }


class ExplanationItemResponse(BaseModel):
    """带解释的推荐项"""
    item: ItemResponse = Field(..., description="推荐内容")
    explanation: str = Field(..., description="推荐理由")
    
    class Config:
        json_schema_extra = {
            "example": {
                "item": {
                    "item_id": "item_001",
                    "content": "如何使用 FastAPI 构建 RESTful API",
                    "tags": ["编程", "Python", "Web开发"],
                    "score": 0.95,
                    "strategy_source": "algorithm"
                },
                "explanation": "基于您对Python和Web开发的兴趣推荐"
            }
        }


class ContentRecommendResponse(BaseModel):
    """内容推荐响应"""
    success: bool = Field(True, description="请求是否成功")
    user_id: str = Field(..., description="用户ID")
    trace_id: str = Field(..., description="追踪ID")
    recommendations: List[ExplanationItemResponse] = Field(..., description="推荐结果列表")
    count: int = Field(..., description="推荐数量")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_id": "user_123",
                "trace_id": "trace_abc_123",
                "recommendations": [
                    {
                        "item": {
                            "item_id": "item_001",
                            "content": "如何使用 FastAPI 构建 RESTful API",
                            "tags": ["编程", "Python", "Web开发"],
                            "score": 0.95,
                            "strategy_source": "algorithm"
                        },
                        "explanation": "基于您对Python和Web开发的兴趣推荐"
                    }
                ],
                "count": 1,
                "timestamp": "2026-01-14T12:00:00"
            }
        }


# ============= 查询推荐相关 Schema =============

class QueryRecommendRequest(BaseModel):
    """查询推荐请求"""
    current_query: str = Field(..., description="当前查询词", example="FastAPI 教程")
    trace_id: Optional[str] = Field(None, description="追踪ID，用于日志追踪", example="trace_xyz_456")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_query": "FastAPI 教程",
                "trace_id": "trace_xyz_456"
            }
        }


class QueryRecommendResponse(BaseModel):
    """查询推荐响应"""
    success: bool = Field(True, description="请求是否成功")
    current_query: str = Field(..., description="当前查询词")
    trace_id: str = Field(..., description="追踪ID")
    recommended_queries: List[str] = Field(..., description="推荐的查询词列表")
    count: int = Field(..., description="推荐数量")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "current_query": "FastAPI 教程",
                "trace_id": "trace_xyz_456",
                "recommended_queries": [
                    "FastAPI 实战项目",
                    "Python Web 框架对比",
                    "FastAPI 性能优化",
                    "RESTful API 设计规范",
                    "FastAPI 异步编程"
                ],
                "count": 5,
                "timestamp": "2026-01-14T12:00:00"
            }
        }


# ============= 通用错误响应 Schema =============

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="请求失败")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "USER_NOT_FOUND",
                "error_message": "用户不存在",
                "timestamp": "2026-01-14T12:00:00"
            }
        }

