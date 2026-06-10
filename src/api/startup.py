"""
FastAPI 启动时加载模型和 Agent。
使用 FlagEmbedding 加载本地 PyTorch 格式的 bge-m3（~/.cache/huggingface/hub/）。
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.config.settings import settings
from src.rag.pipeline import RAGPipeline
# 离线模式：不从 huggingface.co 下载，仅使用本地缓存
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from FlagEmbedding import BGEM3FlagModel

logger = logging.getLogger(__name__)


class AppComponents:
    def __init__(self):
        self.pipeline = None
        self.llm = None
        self.embedding_model = None
        self.agent_graph = None

    @property
    def is_ready(self):
        return all([self.pipeline is not None, self.llm is not None])


components = AppComponents()


class FlagEmbeddingModel:
    """通过 FlagEmbedding 库直接加载 bge-m3，不走 Ollama"""

    def __init__(self):
        self.model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    def encode(self, texts, max_length=512):
        output = self.model.encode(texts, max_length=max_length)
        return {"dense_vecs": output["dense_vecs"].tolist()}


def load_embedding_model():
    logger.info("使用 FlagEmbedding 加载本地 bge-m3 权重（~/.cache/huggingface/hub/）")
    return FlagEmbeddingModel()


def load_llm():
    from langchain_ollama import ChatOllama
    logger.info(f"加载 LLM: {settings.LLM_MODEL}")
    return ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
    )


def load_pipeline(embedding_model):
    logger.info("加载 RAG 管道")
    return RAGPipeline(collection_name="documents", embedding_model=embedding_model)


def load_agent(pipeline, llm):
    from src.agent.graph import build_agent
    return build_agent(pipeline=pipeline, llm=llm, mcp_tools=None)


async def startup_event():
    logger.info("=" * 50)
    logger.info("DocAgent 启动中...")
    logger.info("=" * 50)

    logger.info("[1/4] 加载 Embedding 模型（FlagEmbedding bge-m3）...")
    components.embedding_model = load_embedding_model()

    logger.info("[2/4] 加载 RAG 管道...")
    components.pipeline = load_pipeline(components.embedding_model)
    logger.info(f"   Collection 大小: {components.pipeline.count()}")

    logger.info("[3/4] 加载 LLM...")
    components.llm = load_llm()

    logger.info("[4/4] 加载 Agent...")
    components.agent_graph = load_agent(components.pipeline, components.llm)

    logger.info("=" * 50)
    logger.info(f"✅ DocAgent 启动完成！ http://localhost:{settings.API_PORT}")
    logger.info(f"   Collection: {components.pipeline.count()} 条")
    logger.info("=" * 50)


async def shutdown_event():
    logger.info("DocAgent 关闭中...")
