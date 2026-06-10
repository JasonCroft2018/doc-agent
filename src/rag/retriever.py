"""
混合检索器：向量检索 + BM25 关键词检索 + 交叉编码器重排。

对比课题16：课题16 只用纯向量检索一次定结果。
本实现用 向量+BM25 混合检索取 top_k=20，再交叉编码器重排取 top_k=5。
"""

from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器。

    检索流程：
    1. 向量检索 top_k=20（语义匹配）
    2. BM25 检索 top_k=20（关键词精确匹配）
    3. 合并 + RRF 加权融合
    4. 交叉编码器重排 → top_k=5
    """

    def __init__(
        self,
        collection: Any,
        embedding_model: Any,
        bm25_retriever: Optional[Any] = None,
        reranker: Optional[Any] = None,
        top_k_retrieval: int = 20,
        top_k_rerank: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.collection = collection
        self.embedding_model = embedding_model
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
        self.top_k_retrieval = top_k_retrieval
        self.top_k_rerank = top_k_rerank
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, query: str) -> List[Dict]:
        """混合检索主入口"""
        vec_results = self._vector_search(query)
        kw_results = self._keyword_search(query)
        merged = self._merge_results(vec_results, kw_results)

        if self.reranker and len(merged) > self.top_k_rerank:
            merged = self._rerank(query, merged)

        return merged[:self.top_k_rerank]

    def _vector_search(self, query: str) -> List[Dict]:
        """稠密向量检索"""
        query_vec = self.embedding_model.encode([query], max_length=512)
        embedding = query_vec["dense_vecs"]

        results = self.collection.query(
            query_embeddings=embedding,
            n_results=self.top_k_retrieval,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        for i in range(len(results["documents"][0])):
            items.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score_vector": 1 - results["distances"][0][i],
                "score_keyword": 0.0,
                "score_final": 0.0,
                "_rank_vector": i + 1,
                "_rank_keyword": 999,
            })
        return items

    def _keyword_search(self, query: str) -> List[Dict]:
        """BM25 关键词检索"""
        if self.bm25_retriever is None:
            return []

        try:
            results = self.bm25_retriever.search(query, top_k=self.top_k_retrieval)
            for i, r in enumerate(results):
                r["_rank_vector"] = 999
                r["_rank_keyword"] = i + 1
            return results
        except Exception as e:
            logger.warning(f"BM25 检索失败: {e}")
            return []

    def _merge_results(
        self, vec_results: List[Dict], kw_results: List[Dict]
    ) -> List[Dict]:
        """
        RRF（Reciprocal Rank Fusion）融合。

        score = Σ(1 / (k + rank_i))

        其中 k=60（经验值），rank_i 是每项的排名。
        """
        k = 60
        combined = {}

        for item in vec_results + kw_results:
            content = item["content"]
            if content not in combined:
                combined[content] = {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "score_vector": item["score_vector"],
                    "score_keyword": item["score_keyword"],
                    "score_final": 0.0,
                    "_rank_vector": item.get("_rank_vector", 999),
                    "_rank_keyword": item.get("_rank_keyword", 999),
                }
            else:
                # 合并元信息
                curr = combined[content]
                curr["score_vector"] = max(curr["score_vector"], item["score_vector"])
                curr["score_keyword"] = max(curr["score_keyword"], item["score_keyword"])
                curr["_rank_vector"] = min(curr["_rank_vector"], item.get("_rank_vector", 999))
                curr["_rank_keyword"] = min(curr["_rank_keyword"], item.get("_rank_keyword", 999))

        # RRF 计分
        for content, item in combined.items():
            rrf_vector = 1.0 / (k + item["_rank_vector"]) if item["_rank_vector"] < 999 else 0
            rrf_keyword = 1.0 / (k + item["_rank_keyword"]) if item["_rank_keyword"] < 999 else 0
            item["score_final"] = (
                self.vector_weight * rrf_vector
                + self.keyword_weight * rrf_keyword
            )

        # 按最终分数排序
        results = list(combined.values())
        results.sort(key=lambda x: x["score_final"], reverse=True)
        return results

    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """交叉编码器重排"""
        if not self.reranker:
            return results

        pairs = [(query, r["content"]) for r in results]
        scores = self.reranker.compute_score(pairs, max_length=512)

        for i, r in enumerate(results):
            r["score_rerank"] = float(scores[i])

        results.sort(key=lambda r: r.get("score_rerank", 0), reverse=True)
        return results
