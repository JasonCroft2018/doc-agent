import logging
"""
LangGraph 状态图定义。

编排流程：
User Query → intent 节点 → retrieval 节点（通过 MCP 调用工具）→ output 节点 → Answer

MCP 工具：
- search_documents: 文档检索
- compare_documents: 多文档对比
- check_compliance: 合规检查
"""

from typing import Literal
from src.api.trace_store import write_trace

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import AgentState
from src.agent.nodes.intent import run_intent_detection
from src.agent.nodes.retrieval import run_retrieval, run_retrieval_with_mcp
from src.agent.nodes.output import generate_answer
from src.rag.pipeline import RAGPipeline
from src.mcp.client import MCPToolClient
from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool



def build_agent(
    pipeline: RAGPipeline,
    llm: BaseLLM,
    mcp_tools = None,
) -> StateGraph:
    def _p(msg): print(msg); write_trace(msg)
    """
    构建文档助手 Agent 的状态图。

    Args:
        pipeline: RAG 管道实例
        llm: LLM 实例
        mcp_tools: MCP 工具列表（可选）

    Returns:
        编译好的 StateGraph
    """

    def intent_node(state: AgentState) -> AgentState:
        print("\n🔍 [Trace] doc-agent | 🟢 START | session=" + state.get("thread_id", "default"))
        print("   Input: " + state["query"][:100])
        result = run_intent_detection(state, llm)
        _p("🔍 [Trace] intent |   ├─ intent=" + str(result.get("intent","?")) + " (confidence=" + str(round(result.get("intent_confidence",0),2)) + ")")
        return result

    def security_node(state: AgentState) -> AgentState:
        _p("🔍 [Trace] security |   ├─ SPAN | checking...")
        from src.agent.nodes.security import run_security_check, sanitize_output
        from src.config.settings import settings
        
        # 检测输入（只在 retrieve/compliance 时检查）
        query = state.get("query", "")
        if settings.ENABLE_INJECTION_DETECTION and query:
            safe, _, warning = run_security_check(query)
            if not safe:
                state["answer"] = warning
                state["intent"] = "rejected"
                _p("🔍 [Trace] security |   └─ END | injection detected")
                return state
        
        # 后续 output 节点会做输出脱敏
        _p("🔍 [Trace] security |   └─ END | safe")
        return state

    def retrieval_node(state: AgentState) -> AgentState:
        _p("🔍 [Trace] retrieval |   ├─ SPAN | query=" + state["query"][:80])
        if mcp_tools:
            result = run_retrieval_with_mcp(state, pipeline, llm, mcp_tools)
        else:
            result = run_retrieval(state, pipeline, llm)
        _p("🔍 [Trace] retrieval |   └─ END | chunks=" + str(result.get("retrieved_count",0)))
        return result

    def output_node(state: AgentState) -> AgentState:
        result = generate_answer(state, llm)
        answer_preview = result.get("answer", "")[:80]
        _p("🔍 [Trace] output |   ├─ SPAN | intent=" + str(result.get("intent","?")))
        _p("🔍 [Trace] output |   └─ END | " + answer_preview)
        _p("🔍 [Trace] doc-agent | 🟢 END")
        return result

    def route_after_intent(state: AgentState) -> Literal["retrieval", "output"]:
        intent = state["intent"]
        if intent == "rejected":
            return "output"
        route = "retrieval" if intent in ("retrieve", "compare", "compliance") else "output"
        _p("🔍 [Trace] route |   ├─ intent=" + intent + " → route=" + route)
        return route

    builder = StateGraph(AgentState)

    builder.add_node("intent", intent_node)
    builder.add_node("security", security_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("output", output_node)

    builder.add_edge(START, "intent")
    builder.add_edge("intent", "security")
    builder.add_conditional_edges(
        "security",
        route_after_intent,
        {"retrieval": "retrieval", "output": "output"},
    )
    builder.add_edge("retrieval", "output")
    builder.add_edge("output", END)

    graph = builder.compile(checkpointer=MemorySaver())
    return graph


def run_query(
    graph: StateGraph,
    query: str,
    thread_id: str = "default",
) -> dict:
    """
    运行一次查询。

    Args:
        graph: 编译好的 StateGraph
        query: 用户输入
        thread_id: 对话线程 ID

    Returns:
        最终 AgentState
    """
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "query": query,
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

    events = graph.stream(initial_state, config)

    final_state = initial_state
    for event in events:
        for node_name, state in event.items():
            final_state = state
            pass

    return final_state
