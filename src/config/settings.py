"""
DocAgent 配置管理
所有敏感信息从环境变量读取，不硬编码在代码中。
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-r1:14b")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-m3")

    # ChromaDB
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")

    # LangFuse
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")

    # API
    API_PORT: int = int(os.getenv("API_PORT", "8765"))

    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 20  # 第一次检索取 20 条
    TOP_K_RERANK: int = 5       # 重排后取 5 条

    # 安全
    # Prompt Injection 检测开关
    ENABLE_INJECTION_DETECTION: bool = True
    # 输出脱敏开关
    ENABLE_SANITIZE_OUTPUT: bool = True
    # 合规检查开关
    ENABLE_COMPLIANCE_CHECK: bool = True

    SENSITIVE_PATTERNS: list = [
        r"\d{18}[\dXx]",       # 身份证号
        r"1[3-9]\d{9}",        # 手机号
        r"\d{6,}",             # 连续数字
    ]


settings = Settings()
