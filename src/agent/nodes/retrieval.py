import logging
logger = logging.getLogger(__name__)
"""
RAG 检索节点：根据意图和 Query，调用 RAG 管道检索文档。
复用 Phase 1 的 pipeline 和 query_rewriter。
"""

import logging
from src.agent.state import AgentState
from src.rag.pipeline import RAGPipeline
from src.rag.query_rewriter import QueryRewriter
from langchain_core.language_models import BaseLLM

logger = logging.getLogger(__name__)


def run_retrieval(
    state: AgentState,
    pipeline: RAGPipeline,
    llm: BaseLLM,
) -> AgentState:
    """
    RAG 检索节点执行函数。

    流程：
    1. 只有 retrieve/compliance 意图才检索
    2. 先用 QueryRewriter 改写/拆解 Query
    3. 对每个子查询执行混合检索
    4. 合并去重后写入 state

    Args:
        state: 当前 Agent 状态
        pipeline: RAG 管道实例
        llm: LLM 实例

    Returns:
        更新后的状态
    """
    # 非检索型意图跳过
    if state["intent"] not in ("retrieve", "compare", "compliance"):
        state["context"] = ""
        state["retrieved_chunks"] = []
        state["retrieved_count"] = 0
        return state

    query = state["query"]

    # Step 1: Query 改写
    rewriter = QueryRewriter(llm)
    sub_queries = rewriter.rewrite(query)
    state["rewritten_queries"] = sub_queries
    logger.debug(f"改写后子查询: {sub_queries}")

    # Step 2: 对每个子查询检索
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
        except Exception as e:
            logger.warning(f"子查询检索失败 '{sub_q}': {e}")

    # Step 3: 按分数排序，取 top 10
    all_chunks.sort(key=lambda x: x.get("score_final", 0), reverse=True)
    state["retrieved_chunks"] = all_chunks[:10]
    state["retrieved_count"] = len(all_chunks[:10])

    # Step 4: 构建上下文
    context_parts = []
    for i, chunk in enumerate(state["retrieved_chunks"], 1):
        title = chunk.get("metadata", {}).get("title", "未知")
        source = chunk.get("metadata", {}).get("source", "未知")
        content = chunk.get("content", "")
        context_parts.append(f"[{i}] 来源：{title}（{source}）\n{content}")

    state["context"] = "\n\n---\n\n".join(context_parts)
    logger.debug(f"检索到 {state['retrieved_count']} 个文档块")

    return state


def run_retrieval_with_mcp(
    state: AgentState,
    pipeline: RAGPipeline,
    llm: BaseLLM,
    mcp_tools: list,
) -> AgentState:
    """
    通过 MCP 工具进行检索的节点执行函数。

    根据 intent 选择不同的 MCP 工具：
    - retrieve    → search_documents
    - compare     → compare_documents
    - compliance  → check_compliance

    Args:
        state: 当前 Agent 状态
        pipeline: RAG 管道实例
        llm: LLM 实例
        mcp_tools: MCP LangChain Tool 列表

    Returns:
        更新后的状态
    """
    if state["intent"] not in ("retrieve", "compare", "compliance"):
        state["context"] = ""
        state["retrieved_chunks"] = []
        state["retrieved_count"] = 0
        return state

    query = state["query"]

    # 选择 MCP 工具
    tool_map = {
        "retrieve": "search_documents",
        "compare": "compare_documents",
        "compliance": "check_compliance",
    }
    tool_name = tool_map.get(state["intent"], "search_documents")
    tool = next((t for t in mcp_tools if t.name == tool_name), None)

    if tool is None:
        logger.warning(f"MCP 工具 {tool_name} 未找到，回退到直接检索")
        return run_retrieval(state, pipeline, llm)

    # 调用 MCP 工具
    try:
        if state["intent"] == "compare":
            # 对比工具需要 queries 数组和 dimension
            # Query 改写产出子查询作为对比项
            from src.rag.query_rewriter import QueryRewriter
            rewriter = QueryRewriter(llm)
            sub_queries = rewriter.rewrite(query)
            state["rewritten_queries"] = sub_queries

            result = tool.arun(
                queries=sub_queries,
                dimension="条款差异",
            )
            state["context"] = result
        elif state["intent"] == "compliance":
            result = tool.arun(query=query, industry="通用")
            state["context"] = result
        else:
            result = tool.arun(query=query, top_k=5)
            state["context"] = result

        state["answer"] = state["context"]
        state["retrieved_count"] = 1
        logger.info(f"MCP 工具 {tool_name} 调用成功")

    except Exception as e:
        logger.error(f"MCP 工具调用失败: {e}，回退到直接检索")
        return run_retrieval(state, pipeline, llm)

    return state
