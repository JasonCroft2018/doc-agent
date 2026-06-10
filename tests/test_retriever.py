"""混合检索器测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag.retriever import HybridRetriever


def test_retriever_init():
    """测试检索器初始化"""
    retriever = HybridRetriever(
        collection=None,
        embedding_model=None,
        top_k_retrieval=20,
        top_k_rerank=5,
    )
    assert retriever.top_k_retrieval == 20
    assert retriever.top_k_rerank == 5


def test_retriever_no_rerank():
    """无重排时跳过重排步骤"""
    retriever = HybridRetriever(
        collection=None,
        embedding_model=None,
        reranker=None,
    )
    results = [{"score": 0.5}] * 10
    reranked = retriever._rerank("test", results)
    assert len(reranked) == 10


if __name__ == "__main__":
    test_retriever_init()
    test_retriever_no_rerank()
    print("✅ 所有测试通过！")
