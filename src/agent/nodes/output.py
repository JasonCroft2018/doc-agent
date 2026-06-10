"""
结果整合节点：根据 intent 和检索结果，生成最终回答。
"""

import logging
from src.agent.state import AgentState
from langchain_core.language_models import BaseLLM

logger = logging.getLogger(__name__)


def generate_answer(state: AgentState, llm: BaseLLM) -> AgentState:
    """
    根据意图和上下文生成最终回答。

    不同 intent 使用不同的 prompt 模板：
    - retrieve: 基于上下文回答
    - compare: 对比分析
    - compliance: 风险检查报告
    - chat: 简单问候

    Args:
        state: 当前 Agent 状态
        llm: LLM 实例

    Returns:
        更新后的状态（填充 answer 和 sources）
    """
    intent = state["intent"]

    if intent == "chat":
        state["answer"] = "你好！我是文档助手，可以帮你检索文档、对比合同、检查合规风险。请问有什么可以帮你？"
        state["sources"] = []
        return state

    if not state["retrieved_chunks"]:
        state["answer"] = "没有找到相关文档内容。请换个关键词试试。"
        state["sources"] = []
        return state

    # 根据 intent 选择 prompt 模板
    prompt_templates = {
        "retrieve": _retrieve_prompt,
        "compare": _compare_prompt,
        "compliance": _compliance_prompt,
    }
    prompt_fn = prompt_templates.get(intent, _retrieve_prompt)
    prompt = prompt_fn(state)

    try:
        response = llm.invoke(prompt)
        state["answer"] = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"生成回答失败: {e}")
        state["answer"] = "生成回答时出错，请重试。"

    # 记录来源
    state["sources"] = [
        {
            "title": c.get("metadata", {}).get("title", "未知"),
            "source": c.get("metadata", {}).get("source", "未知"),
            "score": c.get("score_final", 0),
        }
        for c in state["retrieved_chunks"][:3]
    ]

    return state


def _retrieve_prompt(state: AgentState) -> str:
    """检索型回答的 prompt"""
    return f"""你是企业文档助手。请基于以下文档内容回答用户的问��。

文档内容：
{state["context"]}

用户问题：{state["query"]}

要求：
- 基于提供的文档内容回答
- 如果文档内容不足以回答问题，请明确说明
- 引用具体来源
- 用中文回答"""


def _compare_prompt(state: AgentState) -> str:
    """对比型回答的 prompt"""
    return f"""你是企业文档分析助手。请基于以下文档内容进行对比分析。

文档内容：
{state["context"]}

用户要求对比：{state["query"]}

要求：
- 逐项列出差异
- 用表格呈现对比结果
- 标注每项信息来源"""


def _compliance_prompt(state: AgentState) -> str:
    """合规检查的 prompt"""
    return f"""你是企业合规检查助手。请基于以下文档内容进行合规检查。

文档内容：
{state["context"]}

用户要求检查：{state["query"]}

要求：
- 列出所有可能的合规风险点
- 标注风险等级（高/中/低）
- 给出整改建议"""
