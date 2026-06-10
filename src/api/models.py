"""
FastAPI 请求/响应 Pydantic 模型。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ChatRequest(BaseModel):
    """聊天请求"""
    query: str = Field(..., description="用户输入")
    thread_id: str = Field(default="default", description="对话线程 ID")


class SearchRequest(BaseModel):
    """检索请求（直连 RAG，不走 Agent 流程）"""
    query: str = Field(..., description="搜索关键词")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数")


class SourceItem(BaseModel):
    """来源引用"""
    title: str
    source: str
    score: float


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str
    intent: str
    intent_confidence: float
    sources: List[SourceItem] = []
    retrieved_count: int = 0


class SearchResponse(BaseModel):
    """检索响应"""
    results: List[dict]
    total: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    collection_size: int
    model_loaded: bool


class StatsResponse(BaseModel):
    """统计响应"""
    collection_size: int
    total_chunks: int
    total_documents: int
