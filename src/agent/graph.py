"""
LangGraph 状态图定义。

编排流程：
User Query → intent 节点 → retrieval 节点（通过 MCP 调用工具）→ output 节点 → Answer

MCP 工具：
- search_documents: 文档检索
- compare_documents: 多文档对比
- check_compliance: 合规检查
"""

import logging
from typing import Literal

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

logger = logging.getLogger(__name__)


def build_agent(
    pipeline: RAGPipeline,
    llm: BaseLLM,
    mcp_tools = None,
) -> StateGraph:
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
        return run_intent_detection(state, llm)

    def retrieval_node(state: AgentState) -> AgentState:
        # 如果有 MCP 工具，走 MCP 路径；否则走直接调用路径
        if mcp_tools:
            return run_retrieval_with_mcp(state, pipeline, llm, mcp_tools)
        return run_retrieval(state, pipeline, llm)

    def output_node(state: AgentState) -> AgentState:
        return generate_answer(state, llm)

    def route_after_intent(state: AgentState) -> Literal["retrieval", "output"]:
        if state["intent"] in ("retrieve", "compare", "compliance"):
            return "retrieval"
        return "output"

    builder = StateGraph(AgentState)

    builder.add_node("intent", intent_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("output", output_node)

    builder.add_edge(START, "intent")
    builder.add_conditional_edges(
        "intent",
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
            logger.debug(f"节点 {node_name} 完成")

    return final_state
