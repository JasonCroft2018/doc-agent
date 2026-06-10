"""Agent 核心测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.state import AgentState
from src.agent.nodes.intent import classify_intent, _keyword_fallback


def test_intent_fallback_chat():
    """关键词兜底：问候→chat"""
    intent, conf = _keyword_fallback("你好")
    assert intent == "chat"


def test_intent_fallback_compare():
    """关键词兜底：对比→compare"""
    intent, conf = _keyword_fallback("A和B有什么区别")
    assert intent == "compare"


def test_intent_fallback_compliance():
    """关键词兜底：合规→compliance"""
    intent, conf = _keyword_fallback("这个合同有没有风险")
    assert intent == "compliance"


def test_intent_fallback_default():
    """无关键词→retrieve"""
    intent, conf = _keyword_fallback("什么是Transformer")
    assert intent == "retrieve"


def test_state_defaults():
    """AgentState 默认值"""
    state: AgentState = {
        "query": "test",
        "intent": "",
        "intent_confidence": 0.0,
        "rewritten_queries": [],
        "retrieved_chunks": [],
        "retrieved_count": 0,
        "context": "",
        "answer": "",
        "sources": [],
        "error": None,
        "max_retries": 2,
        "retry_count": 0,
    }
    assert state["query"] == "test"
    assert state["max_retries"] == 2


if __name__ == "__main__":
    test_intent_fallback_chat()
    test_intent_fallback_compare()
    test_intent_fallback_compliance()
    test_intent_fallback_default()
    test_state_defaults()
    print("✅ 所有测试通过！")
