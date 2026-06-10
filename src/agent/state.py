"""
Agent 状态类型定义。

StateGraph 中流转的数据结构，所有节点读写这个状态。
"""

from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    """Agent 状态"""
    # 输入
    query: str                              # 用户原始输入

    # 意图识别
    intent: str                             # 识别后的意图
    intent_confidence: float                # 置信度

    # 检索
    rewritten_queries: List[str]            # 改写后的子查询
    retrieved_chunks: List[dict]            # 检索到的文档块
    retrieved_count: int                    # 检索到的数量

    # 上下文与输出
    context: str                            # 整合后的上下文
    answer: str                             # 最终回答
    sources: List[dict]                     # 来源引用

    # 状态控制
    error: Optional[str]                    # 错误信息
    max_retries: int                        # 最大重试次数
    retry_count: int                        # 当前重试次数
