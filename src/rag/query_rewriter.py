"""
Query 改写器：用 LLM 将用户 Query 改写/拆解，提升检索命中率。

对比课题16：课题16 直接将原始 Query 拿去向量检索。
本实现先用 LLM 将 Query 拆解为多个子查询，再分别检索后合并结果。
"""

from typing import List, Optional
from langchain_core.language_models import BaseLLM


class QueryRewriter:
    """
    Query 改写器。

    能力：
    1. 拆解复合问题为多个子查询
       "Transformer 的注意力机制怎么算的？"
       → ["Transformer 注意力机制", "Self-Attention 计算", "QKV 矩阵运算"]
    2. 补充同义术语
       "注意力" → "Attention", "Self-Attention"
    3. 口语化 → 技术用语
       "怎么算的" → "计算过程", "数学推导"
    """

    def __init__(self, llm: BaseLLM):
        """
        Args:
            llm: LangChain LLM 实例（用于 Query 改写）
        """
        self.llm = llm

    def rewrite(self, query: str, max_queries: int = 4) -> List[str]:
        """
        改写 Query，返回多个搜索子查询。

        Args:
            query: 用户原始查询
            max_queries: 最多返回几个子查询

        Returns:
            子查询列表（包含原始查询）
        """
        prompt = self._build_prompt(query)

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            keywords = [k.strip() for k in content.split(",") if k.strip()]
        except Exception as e:
            logger.warning(f"Query 改写失败: {e}，使用原始查询")
            keywords = []

        # 去重 + 保留原始查询
        all_queries = [query]
        for k in keywords:
            if k.lower() != query.lower() and k not in all_queries:
                all_queries.append(k)

        return all_queries[:max_queries]

    def _build_prompt(self, query: str) -> str:
        """构建改写提示词"""
        return f"""你是一个搜索专家。请将用户的查询改写/拆解为 3 个更适合向量检索的搜索关键词。

要求：
- 拆解复合问题为独立关键词
- 补充同义技术术语
- 将口语转为书面/技术用语
- 每个关键词不超过 15 个字
- 用逗号分隔，不要编号

例子：
用户："Transformer 的注意力机制是怎么算的？"
输出：Transformer 注意力机制, Self-Attention 计算, QKV 矩阵运算

用户："Mamba 模型和 SSM 有什么关系？"
输出：Mamba 状态空间模型, SSM 原理, 选择性状态空间

用户："{query}"
输出："""
