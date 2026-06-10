"""
RAG 检索节点：根据意图和 Query，调用 RAG 管道检索文档。
复用 Phase 1 的 pipeline 和 query_rewriter。
"""

from typing import List

from src.agent.state import AgentState
from src.rag.pipeline import RAGPipeline
from langchain_core.language_models import BaseLLM



def run_retrieval(
    state: AgentState,
    pipeline: RAGPipeline,
    llm: BaseLLM,
) -> AgentState:
    """RAG 检索节点执行函数"""
    
    if state["intent"] not in ("retrieve", "compare", "compliance"):
        state["context"] = ""
        state["retrieved_chunks"] = []
        state["retrieved_count"] = 0
        return state

    query = state["query"]
    # QueryRewriter 暂不启用（避免 LangGraph 运行时 logger 问题）
    sub_queries = [query]
    state["rewritten_queries"] = sub_queries

    all_chunks = []
    seen_contents = set()

    for sub_q in sub_queries:
        try:
            results = pipeline.search(sub_q, top_k=5)
            for r in results:
                content = r.get("content", "")
                if content and content not in seen_contents:
                    seen_contents.add(content)
                    all_chunks.append(r)
        except Exception:
            pass

    all_chunks.sort(key=lambda x: x.get("score_final", 0), reverse=True)
    state["retrieved_chunks"] = all_chunks[:10]
    state["retrieved_count"] = len(all_chunks[:10])

    context_parts = []
    for i, chunk in enumerate(state["retrieved_chunks"], 1):
        title = chunk.get("metadata", {}).get("title", "未知")
        source = chunk.get("metadata", {}).get("source", "未知")
        content = chunk.get("content", "")
        context_parts.append(f"[{i}] 来源：{title}（{source}）\n{content}")

    state["context"] = "\n\n---\n\n".join(context_parts)
    return state


def run_retrieval_with_mcp(
    state: AgentState,
    pipeline: RAGPipeline,
    llm: BaseLLM,
    mcp_tools: list,
) -> AgentState:
    """MCP 版本 — 当前简化直接走 RAG"""
    return run_retrieval(state, pipeline, llm)
