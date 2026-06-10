"""
BM25 关键词检索器。

补充向量检索无法处理的精确匹配问题：
- 合同编号 "CON-2025-038"
- 专业术语 "QKV"
- 人名/地名等专有名词

使用 rank_bm25 库，纯 Python 实现，轻量级。
"""

import pickle
import os
import re
import logging
from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25 关键词检索器。

    用法：
        retriever = BM25Retriever()
        retriever.build_index(chunks)      # 构建索引
        results = retriever.search(query)   # 检索
        retriever.save_index(path)          # 持久化
        retriever.load_index(path)          # 加载
    """

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[str] = []
        self.metadatas: List[Dict] = []

    def build_index(self, documents: List[Dict[str, str]]) -> None:
        """
        构建 BM25 索引。

        Args:
            documents: 文档列表，每项 {"content": str, ...}
        """
        self.chunks = []
        self.metadatas = []

        for doc in documents:
            content = doc.get("content", "")
            if not content.strip():
                continue

            self.chunks.append(content)
            self.metadatas.append({
                k: v for k, v in doc.items() if k != "content"
            })

        # 分词并建立 BM25 索引
        tokenized = [self._tokenize(c) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)

        logger.info(f"BM25 索引构建完成：{len(self.chunks)} 条")

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        BM25 检索。

        Args:
            query: 查询字符串
            top_k: 返回结果数

        Returns:
            检索结果列表
        """
        if self.bm25 is None:
            logger.warning("BM25 索引未构建")
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # 按分数排序
        scored = [(i, scores[i]) for i in range(len(scores))]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, score in scored[:top_k]:
            if score > 0:
                results.append({
                    "content": self.chunks[i],
                    "metadata": self.metadatas[i] if i < len(self.metadatas) else {},
                    "score_vector": 0.0,
                    "score_keyword": float(score),
                    "score_final": 0.0,
                })

        return results

    def save_index(self, path: str) -> None:
        """持久化 BM25 索引到磁盘"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "chunks": self.chunks,
            "metadatas": self.metadatas,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"BM25 索引已保存到 {path}")

    def load_index(self, path: str) -> bool:
        """从磁盘加载 BM25 索引"""
        if not os.path.exists(path):
            logger.warning(f"BM25 索引文件不存在: {path}")
            return False

        with open(path, "rb") as f:
            data = pickle.load(f)

        self.chunks = data["chunks"]
        self.metadatas = data["metadatas"]
        tokenized = [self._tokenize(c) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)

        logger.info(f"BM25 索引已加载：{len(self.chunks)} 条")
        return True

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        中文 + 英文分词。

        策略：中文按字切（BM25 对中文按字效果好），英文按空格切。
        """
        # 中文部分：按字切
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
        # 英文部分：按空格和标点切
        english_tokens = re.findall(r"[a-zA-Z0-9\+\-\.]+", text.lower())
        return chinese_chars + english_tokens
