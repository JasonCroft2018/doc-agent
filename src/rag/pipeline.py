"""
RAG 管道主入口：整合切片 → 向量化 → 入库 → 检索全流程。

对比课题16：课题16 将索引和搜索写在一个脚本中。
本实现模块化拆分：splitter → retriever → query_rewriter，
每个模块可独立测试和替换。
"""

import os
import logging
from typing import List, Dict, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config.settings import settings
from src.rag.splitter import chunk_by_semantic_boundary
from src.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG 管道：文档索引 + 混合检索一体化。

    用法：
        pipeline = RAGPipeline()
        pipeline.build_index(documents)     # 构建索引
        results = pipeline.search(query)    # 检索
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_model: Optional[Any] = None,
        reranker: Optional[Any] = None,
    ):
        """
        Args:
            collection_name: ChromaDB collection 名称
            embedding_model: BGE-M3 模型实例（可选，延迟加载）
            reranker: 交叉编码器重排模型实例（可选）
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.reranker = reranker

        # 初始化 ChromaDB 客户端
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # 获取或创建 collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            count = self.collection.count()
            logger.info(f"加载已有 collection: {collection_name} ({count} 条)")
        except Exception:
            self.collection = self.client.create_collection(name=collection_name)
            logger.info(f"创建新 collection: {collection_name}")

        # 初始化检索器
        self.retriever = HybridRetriever(
            collection=self.collection,
            embedding_model=self.embedding_model,
            reranker=self.reranker,
            top_k_retrieval=settings.TOP_K_RETRIEVAL,
            top_k_rerank=settings.TOP_K_RERANK,
        )

    def build_index(self, documents: List[Dict[str, str]]) -> Dict:
        """
        构建文档索引。

        Args:
            documents: 文档列表，每项 {"title": str, "content": str, "source": str}

        Returns:
            索引统计信息
        """
        all_chunks = []
        all_ids = []
        all_metadatas = []

        for doc in documents:
            # Step 1: 语义切片
            chunks = chunk_by_semantic_boundary(
                doc["content"],
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )

            # Step 2: 准备数据
            for i, chunk in enumerate(chunks):
                chunk_id = f"{hash(doc['source'])}_{i}"
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
                all_metadatas.append({
                    "title": doc["title"],
                    "source": doc["source"],
                    "chunk_index": i,
                })

        # Step 3: 向量化并入库
        if all_chunks:
            # 分批写入，避免单次过大
            BATCH_SIZE = 100
            for i in range(0, len(all_chunks), BATCH_SIZE):
                end = min(i + BATCH_SIZE, len(all_chunks))
                batch_texts = all_chunks[i:end]

                # 向量化
                embeddings = self._embed_batch(batch_texts)

                self.collection.add(
                    ids=all_ids[i:end],
                    documents=batch_texts,
                    metadatas=all_metadatas[i:end],
                    embeddings=embeddings,
                )

        return {
            "documents": len(documents),
            "chunks": len(all_chunks),
            "collection": self.collection.count(),
        }

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        混合检索。

        Args:
            query: 用户查询
            top_k: 返回结果数（覆盖默认值）

        Returns:
            检索结果列表
        """
        if top_k:
            self.retriever.top_k_rerank = top_k
        return self.retriever.retrieve(query)

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量向量化"""
        if self.embedding_model is None:
            raise ValueError("embedding_model 未设置，无法向量化")

        output = self.embedding_model.encode(texts, max_length=512)
        return output["dense_vecs"]

    def count(self) -> int:
        """返回 collection 中的文档数"""
        return self.collection.count()

    def clear(self):
        """清空 collection"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(name=self.collection_name)
        logger.info(f"已清空 collection: {self.collection_name}")


# 解决 Optional[Any] 的引用问题
from typing import Any
