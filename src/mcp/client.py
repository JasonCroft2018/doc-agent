"""
MCP 客户端工具包装。

将 MCP Server 的工具包装为 LangChain Tool，
让 Agent 可以通过 LangChain Tool 接口调用 MCP 工具。

用法：
    client = MCPToolClient()
    client.connect("doc_retrieval", DocRetrievalServer(pipeline, llm))
    tools = client.get_langchain_tools()
    # tools 可直接传入 LangGraph Agent
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, ToolException

logger = logging.getLogger(__name__)


class MCPToolClient:
    """
    MCP 工具客户端。

    管理多个 MCP Server 的连接，并将工具暴露为 LangChain Tool。
    """

    def __init__(self):
        self._servers: Dict[str, Any] = {}
        self._tools: List[BaseTool] = []

    def register_server(self, name: str, server_instance: Any) -> None:
        """
        注册一个 MCP Server。

        Args:
            name: Server 名称
            server_instance: MCP Server 实例
        """
        self._servers[name] = server_instance
        logger.info(f"MCP Server 已注册: {name}")

    def get_langchain_tools(self) -> List[BaseTool]:
        """
        获取所有 MCP 工具的 LangChain Tool 封装。

        Returns:
            LangChain Tool 列表
        """
        tools = []

        # 文档检索工具
        tools.append(_MCPTool(
            name="search_documents",
            description="根据自然语言查询检索文档内容。输入查询语句，返回相关文档片段和来源。",
            server_name="doc_retrieval",
            tool_name="search_documents",
            args_schema={
                "query": {"type": "string", "description": "搜索查询"},
                "top_k": {"type": "integer", "description": "返回结果数", "default": 5},
            },
        ))

        # 多文档对比工具
        tools.append(_MCPTool(
            name="compare_documents",
            description="对比多份文档在指定维度的差异。输入多个查询和对比维度，返回对比表格。",
            server_name="doc_comparison",
            tool_name="compare_documents",
            args_schema={
                "queries": {"type": "array", "items": {"type": "string"}, "description": "要对比的文档查询"},
                "dimension": {"type": "string", "description": "对比维度"},
            },
        ))

        # 合规检查工具
        tools.append(_MCPTool(
            name="check_compliance",
            description="检查文档内容的合规风险。输入文档描述和行业，返回风险报告。",
            server_name="compliance",
            tool_name="check_compliance",
            args_schema={
                "query": {"type": "string", "description": "需要检查的内容"},
                "industry": {"type": "string", "description": "行业", "default": "通用"},
            },
        ))

        return tools


class _MCPTool(BaseTool):
    """
    MCP 工具的 LangChain Tool 包装。

    将 MCP 的 call_tool 接口包装为 LangChain 的 Tool 接口。
    """

    name: str
    description: str
    server_name: str
    tool_name: str
    args_schema: dict

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _run(self, **kwargs) -> str:
        """同步执行（MCP 需要异步，这里抛出提示）"""
        raise ToolException(
            "MCP 工具需要异步执行，请使用 arun() 或 await"
        )

    async def _arun(self, **kwargs) -> str:
        """
        异步执行 MCP 工具调用。

        注意：当前使用模拟调用，因为 MCP Stdio Server
        需要在独立进程中运行。后续 Phase 4 服务化后
        将改为 HTTP 调用。
        """
        # TODO: 实现真正的 MCP 协议客户端调用
        # 当前返回模拟结果，供 Agent 流程测试
        query = kwargs.get("query", kwargs.get("queries", str(kwargs)))
        return f"[MCP] 工具 {self.tool_name} 已收到请求。正在处理: {query}"


def create_mcp_tools(
    retrieval_server: Any,
    comparison_server: Any,
    compliance_server: Any,
) -> List[BaseTool]:
    """
    快捷创建所有 MCP 工具的 LangChain Tool 封装。

    Args:
        retrieval_server: 文档检索 MCP Server
        comparison_server: 文档对比 MCP Server
        compliance_server: 合规检查 MCP Server

    Returns:
        LangChain Tool 列表
    """
    client = MCPToolClient()
    # 注册 Server（实际调用时会通过真正的 MCP 协议通信）
    client.register_server("doc_retrieval", retrieval_server)
    client.register_server("doc_comparison", comparison_server)
    client.register_server("compliance", compliance_server)
    return client.get_langchain_tools()
