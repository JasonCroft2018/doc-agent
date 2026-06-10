"""
意图识别节点：判断用户 Query 属于哪种任务类型。

意图分类：
- retrieve: 常规检索（"XX 条款是什么"）
- compare: 多文档对比（"A 和 B 的区别"）
- compliance: 合规检查（"有没有风险"）
- chat: 闲聊/问候（仅对话，不检索）
"""

from typing import Literal
from langchain_core.language_models import BaseLLM
from src.agent.state import AgentState


# 意图类型
IntentType = Literal["retrieve", "compare", "compliance", "chat"]

# 意图匹配关键词（作为 LLM 判断的补充）
INTENT_KEYWORDS = {
    "compare": ["对比", "区别", "差异", "不同", "vs", "versus", "比较"],
    "compliance": ["合规", "风险", "检查", "违法", "违规", "审计", "安全"],
    "chat": ["你好", "嗨", "help", "谢谢", "你是谁", "能做什么"],
}


def classify_intent(query: str, llm: BaseLLM) -> tuple[IntentType, float]:
    """
    用 LLM 判断 Query 的意图。

    Args:
        query: 用户输入
        llm: LLM 实例

    Returns:
        (意图类型, 置信度)
    """
    prompt = f"""你是一个任务分类器。判断用户的问题是以下哪种类型：

- retrieve: 查询/检索信息（如"XX是什么"、"XX条款"）
- compare: 对比/比较（如"有什么区别"、"哪个更好"）
- compliance: 合规/风险检查（如"有没有风险"、"是否合规"）
- chat: 问候/闲聊（如"你好"、"谢谢"）

只返回类型名称和置信度，格式：类型|置信度(0-1)
例如：retrieve|0.95

用户问题：{query}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parts = content.strip().split("|")
        intent = parts[0].strip().lower()
        confidence = float(parts[1]) if len(parts) > 1 else 0.8

        if intent not in ("retrieve", "compare", "compliance", "chat"):
            intent = "retrieve"
            confidence = 0.5
    except Exception:
        # LLM 失败时，用关键词兜底
        intent, confidence = _keyword_fallback(query)

    return intent, min(confidence, 1.0)


def _keyword_fallback(query: str) -> tuple[IntentType, float]:
    """关键词兜底分类"""
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query.lower():
                return intent, 0.6
    return "retrieve", 0.5


def run_intent_detection(state: AgentState, llm: BaseLLM) -> AgentState:
    """
    意图识别节点执行函数。

    Args:
        state: 当前 Agent 状态
        llm: LLM 实例

    Returns:
        更新后的状态（填充 intent 和 intent_confidence）
    """
    intent, confidence = classify_intent(state["query"], llm)
    state["intent"] = intent
    state["intent_confidence"] = confidence
    return state
