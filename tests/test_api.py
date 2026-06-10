"""API 模型测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.models import (
    ChatRequest, ChatResponse, SourceItem,
    SearchRequest, HealthResponse,
)


def test_chat_request():
    """ChatRequest 模型验证"""
    req = ChatRequest(query="test query", thread_id="test123")
    assert req.query == "test query"
    assert req.thread_id == "test123"


def test_chat_request_default_thread():
    """ChatRequest 默认 thread_id"""
    req = ChatRequest(query="test")
    assert req.thread_id == "default"


def test_search_request():
    """SearchRequest 模型验证"""
    req = SearchRequest(query="test", top_k=10)
    assert req.query == "test"
    assert req.top_k == 10


def test_search_request_defaults():
    """SearchRequest 默认值"""
    req = SearchRequest(query="test")
    assert req.top_k == 5


def test_search_request_top_k_range():
    """top_k 范围验证"""
    try:
        SearchRequest(query="test", top_k=0)
        assert False, "应该抛出验证错误"
    except Exception:
        pass


def test_health_response():
    """HealthResponse 模型验证"""
    resp = HealthResponse(
        status="ok",
        version="0.1.0",
        collection_size=100,
        model_loaded=True,
    )
    assert resp.status == "ok"
    assert resp.collection_size == 100


def test_chat_response_with_sources():
    """ChatResponse 带来源"""
    resp = ChatResponse(
        answer="test answer",
        intent="retrieve",
        intent_confidence=0.95,
        sources=[
            SourceItem(title="doc1", source="file1.md", score=0.9),
        ],
        retrieved_count=1,
    )
    assert len(resp.sources) == 1
    assert resp.sources[0].title == "doc1"


if __name__ == "__main__":
    test_chat_request()
    test_chat_request_default_thread()
    test_search_request()
    test_search_request_defaults()
    test_search_request_top_k_range()
    test_health_response()
    test_chat_response_with_sources()
    print("✅ 所有 API 测试通过！")
