"""
MCP Server 定义。

提供三个工具 Server：
1. doc_retrieval  — 文档检索
2. doc_comparison — 多文档对比
3. compliance     — 合规检查

通信方式：Stdio（进程内通信）
"""

import json
import logging
from typing import Any, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult
from pydantic import BaseModel

from src.rag.pipeline import RAGPipeline
from src.rag.query_rewriter import QueryRewriter
from langchain_core.language_models import BaseLLM

logger = logging.getLogger(__name__)


class DocRetrievalServer:
    """
    文档检索 MCP Server。

    工具：
    - search_documents: 根据 Query 检索相关文档
    """

    def __init__(self, pipeline: RAGPipeline, llm: BaseLLM):
        self.pipeline = pipeline
        self.llm = llm
        self.rewriter = QueryRewriter(llm)
        self.server = Server("doc-retrieval")

        self._register_tools()

    def _register_tools(self):
        """注册工具"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="search_documents",
                    description="根据自然语言查询检索相关文档内容。支持语义搜索和关键词搜索。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户的自然语言查询",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回结果数量（默认 5）",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict
        ) -> list[TextContent]:
            if name == "search_documents":
                return await self._handle_search(arguments)
            raise ValueError(f"未知工具: {name}")

        @self.server.list_prompts()
        async def list_prompts():
            return []

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict):
            return None

    async def _handle_search(self, args: dict) -> list[TextContent]:
        """处理检索请求"""
        query = args["query"]
        top_k = args.get("top_k", 5)

        # Query 改写
        sub_queries = self.rewriter.rewrite(query)

        # 对所有子查询检索
        all_results = []
        seen = set()
        for sub_q in sub_queries:
            results = self.pipeline.search(sub_q, top_k=top_k)
            for r in results:
                content = r.get("content", "")
                if content and content not in seen:
                    seen.add(content)
                    all_results.append(r)

        # 格式化结果
        formatted = []
        for i, r in enumerate(all_results[:top_k], 1):
            title = r.get("metadata", {}).get("title", "未知")
            source = r.get("metadata", {}).get("source", "未知")
            score = r.get("score_final", 0)
            content = r.get("content", "")[:300]
            formatted.append(
                f"[{i}] {title}（{source}）| 相关度: {score:.2f}\n{content}"
            )

        result_text = (
            f"找到 {len(all_results)} 条相关结果：\n\n"
            + "\n\n---\n\n".join(formatted)
            if formatted
            else "未找到相关文档。"
        )

        return [TextContent(type="text", text=result_text)]

    async def run(self):
        """运行 Server（使用 stdio 通信）"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="doc-retrieval",
                    server_version="0.1.0",
                ),
            )


class DocComparisonServer:
    """
    多文档对比 MCP Server。

    工具：
    - compare_documents: 对比多份文档的指定维度
    """

    def __init__(self, pipeline: RAGPipeline, llm: BaseLLM):
        self.pipeline = pipeline
        self.llm = llm
        self.server = Server("doc-comparison")

        self._register_tools()

    def _register_tools(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="compare_documents",
                    description="对比多份文档在指定维度的差异。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "需要对比的文档查询（每份文档一个查询）",
                            },
                            "dimension": {
                                "type": "string",
                                "description": "对比维度（如：付款条款、有效期、违约责任）",
                            },
                        },
                        "required": ["queries", "dimension"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict
        ) -> list[TextContent]:
            if name == "compare_documents":
                return await self._handle_compare(arguments)
            raise ValueError(f"未知工具: {name}")

        @self.server.list_prompts()
        async def list_prompts():
            return []

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict):
            return None

    async def _handle_compare(self, args: dict) -> list[TextContent]:
        """处理对比请求"""
        queries = args["queries"]
        dimension = args["dimension"]

        # 对每个查询分别检索
        doc_results = []
        for q in queries:
            results = self.pipeline.search(q, top_k=3)
            if results:
                doc_results.append({
                    "query": q,
                    "content": results[0].get("content", ""),
                    "source": results[0].get("metadata", {}).get("source", "未知"),
                })

        # 用 LLM 做对比分析
        docs_text = "\n\n===\n\n".join(
            f"文档：{d['source']}\n查询：{d['query']}\n内容：{d['content'][:500]}"
            for d in doc_results
        )

        prompt = (
            f"请对比以下文档在「{dimension}」维度的差异。\n\n"
            f"{docs_text}\n\n"
            f"要求：\n"
            f"- 逐项列出差异\n"
            f"- 用表格展示\n"
            f"- 标注每项来源"
        )

        response = self.llm.invoke(prompt)
        comparison = response.content if hasattr(response, "content") else str(response)

        return [TextContent(type="text", text=comparison)]

    async def run(self):
        """运行 Server"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="doc-comparison",
                    server_version="0.1.0",
                ),
            )


class ComplianceServer:
    """
    合规检查 MCP Server。

    工具：
    - check_compliance: 检查文档条款是否符合合规要求
    """

    def __init__(self, pipeline: RAGPipeline, llm: BaseLLM):
        self.pipeline = pipeline
        self.llm = llm
        self.server = Server("compliance")

        self._register_tools()

    def _register_tools(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="check_compliance",
                    description="检查文档内容是否存在合规风险。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "需要检查的文档或条款描述",
                            },
                            "industry": {
                                "type": "string",
                                "description": "所属行业（如：金融、医疗、零售）",
                                "default": "通用",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict
        ) -> list[TextContent]:
            if name == "check_compliance":
                return await self._handle_compliance(arguments)
            raise ValueError(f"未知工具: {name}")

        @self.server.list_prompts()
        async def list_prompts():
            return []

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict):
            return None

    async def _handle_compliance(self, args: dict) -> list[TextContent]:
        """处理合规检查请求"""
        query = args["query"]
        industry = args.get("industry", "通用")

        # 检索相关文档和合规规则
        results = self.pipeline.search(query, top_k=5)

        context = "\n\n".join(
            r.get("content", "") for r in results
        ) if results else "未找到相关文档。"

        prompt = (
            f"你是一个合规检查专家。请对以下内容进行合规风险检查。\n\n"
            f"所属行业：{industry}\n\n"
            f"检查内容：\n{context}\n\n"
            f"用户关注：{query}\n\n"
            f"要求输出格式：\n"
            f"1. 风险点列表（每条含：风险描述、风险等级[高/中/低]、相关条款）\n"
            f"2. 整体风险评估\n"
            f"3. 整改建议"
        )

        response = self.llm.invoke(prompt)
        report = response.content if hasattr(response, "content") else str(response)

        return [TextContent(type="text", text=report)]

    async def run(self):
        """运行 Server"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="compliance",
                    server_version="0.1.0",
                ),
            )
