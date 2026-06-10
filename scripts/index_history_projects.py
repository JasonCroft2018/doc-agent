"""
索引文档到 DocAgent 知识库。

用法：
    # 默认扫描历史项目目录
    python3 scripts/index_history_projects.py
    
    # 指定目录
    python3 scripts/index_history_projects.py /path/to/docs
"""

import os
import sys
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config.settings import settings
from src.rag.pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {".txt", ".md", ".json", ".sql", ".csv", ".xml", ".yaml", ".yml", ".properties"}

def read_text(filepath):
    for enc in ["utf-8", "gbk"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except: continue
    return None

def scan(base_dir):
    documents, skipped = [], 0
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTS:
                content = read_text(fpath)
                if content and len(content.strip()) > 20:
                    rel = os.path.relpath(fpath, base_dir)
                    project = rel.split(os.sep)[0] if os.sep in rel else "default"
                    documents.append({"title": rel, "content": content, "source": fpath, "project": project})
                else: skipped += 1
            else: skipped += 1
    logger.info(f"扫描: {len(documents)} 文档, {skipped} 跳过")
    return documents

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else input("请输入文档目录路径: ").strip()
    if not os.path.exists(target):
        logger.error(f"路径不存在: {target}")
        sys.exit(1)
    
    docs = scan(target)
    if not docs:
        logger.warning("未找到可索引的文档")
        return
    
    import requests
    class OllamaEmbedding:
        def encode(self, texts, max_length=512):
            if isinstance(texts, str): texts = [texts]
            dense_vecs = []
            for text in texts:
                resp = requests.post(f"{settings.OLLAMA_BASE_URL}/api/embeddings", json={"model": settings.EMBEDDING_MODEL, "prompt": text}, timeout=30)
                dense_vecs.append(resp.json()["embedding"] if resp.status_code == 200 else [0.0]*1024)
            return {"dense_vecs": dense_vecs}

    pipeline = RAGPipeline(collection_name="documents", embedding_model=OllamaEmbedding())
    result = pipeline.build_index(docs)
    logger.info(f"完成: {result}")

if __name__ == "__main__":
    main()
