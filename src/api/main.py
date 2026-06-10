"""
FastAPI 主应用。

端点：
- POST /api/chat    — 对话（走 Agent 流程）
- POST /api/search  — 检索（直连 RAG）
- GET  /api/health  — 健康检查
- GET  /api/stats   — 索引统计

启动：
    uvicorn src.api.main:app --reload --port 8765
"""

import logging
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.api.models import (
    ChatRequest, ChatResponse, SourceItem,
    SearchRequest, SearchResponse,
    HealthResponse, StatsResponse,
)
from src.api.startup import components, startup_event, shutdown_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await startup_event()
    yield
    await shutdown_event()



app = FastAPI(
    title="DocAgent — 企业文档智能助手",
    description="基于 LangGraph + MCP + RAG 的企业文档智能 API",
    version="0.1.0",
    lifespan=lifespan,
)


# 根路径 — Web UI 页面
from src.api.ui_html import HTML_PAGE
from fastapi.responses import HTMLResponse

@app.get("/")
async def index():
    """Web UI 页面"""
    return HTMLResponse(content=HTML_PAGE)


# CORS 配置（允许 Streamlit 等前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API 端点
# ============================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok" if components.is_ready else "loading",
        version="0.1.0",
        collection_size=components.pipeline.count() if components.pipeline else 0,
        model_loaded=components.is_ready,
    )


@app.get("/api/trace/latest")
async def get_latest_trace():
    """获取最近的 Trace 日志"""
    from src.api.trace_store import get_latest_trace
    from fastapi.responses import JSONResponse
    lines = get_latest_trace()
    return JSONResponse({"lines": lines, "total": len(lines)})


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """索引统计"""
    if not components.pipeline:
        raise HTTPException(status_code=503, detail="服务未就绪")

    return StatsResponse(
        collection_size=components.pipeline.count(),
        total_chunks=components.pipeline.count(),
        total_documents=0,  # TODO: 追踪文档数
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口。

    走完整的 Agent 流程：
    Query → 意图识别 → RAG 检索（通过 MCP） → 生成回答

    示例：
        curl -X POST http://localhost:8765/api/chat \\
            -H "Content-Type: application/json" \\
            -d '{"query": "Transformer 的注意力机制是什么？"}'
    """
    if not components.is_ready:
        raise HTTPException(status_code=503, detail="服务未就绪，请稍后重试")

    from src.agent.graph import run_query

    try:
        result = run_query(
            graph=components.agent_graph,
            query=request.query,
            thread_id=request.thread_id,
        )

        return ChatResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", ""),
            intent_confidence=result.get("intent_confidence", 0.0),
            sources=[
                SourceItem(title=s["title"], source=s["source"], score=s["score"])
                for s in result.get("sources", [])
            ],
            retrieved_count=result.get("retrieved_count", 0),
        )

    except Exception as e:
        logger.error(f"Agent 调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    检索接口（直连 RAG，不走 Agent 流程）。

    用于快速验证检索效果，不经过意图识别和回答生成。

    示例：
        curl -X POST http://localhost:8765/api/search \\
            -H "Content-Type: application/json" \\
            -d '{"query": "Transformer 注意力", "top_k": 3}'
    """
    if not components.pipeline:
        raise HTTPException(status_code=503, detail="服务未就绪")

    try:
        results = components.pipeline.search(
            query=request.query,
            top_k=request.top_k,
        )

        formatted = []
        for r in results:
            formatted.append({
                "content": r.get("content", ""),
                "title": r.get("metadata", {}).get("title", ""),
                "source": r.get("metadata", {}).get("source", ""),
                "score": round(r.get("score_final", 0), 4),
            })

        return SearchResponse(results=formatted, total=len(formatted))

    except Exception as e:
        logger.error(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
        log_level="info",
    )
