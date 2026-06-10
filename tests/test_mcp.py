"""
MCP 测试。

注意：MCP Python SDK 尚未发布到 PyPI，
MCP Server 层的测试需要在安装 SDK 后运行。
当前测试覆盖 MCP 客户端工具包装层。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mcp.client import MCPToolClient, create_mcp_tools


def test_mcp_tool_client_init():
    """MCP 客户端初始化"""
    client = MCPToolClient()
    tools = client.get_langchain_tools()
    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "search_documents" in tool_names
    assert "compare_documents" in tool_names
    assert "check_compliance" in tool_names


def test_mcp_tool_descriptions():
    """工具描述不为空且有实际内容"""
    client = MCPToolClient()
    tools = client.get_langchain_tools()
    for t in tools:
        assert t.description, f"工具 {t.name} 描述为空"
        assert len(t.description) > 10


def test_mcp_tool_has_args():
    """工具参数定义完整"""
    client = MCPToolClient()
    tools = client.get_langchain_tools()

    search = [t for t in tools if t.name == "search_documents"][0]
    assert "query" in search.args_schema
    assert "top_k" in search.args_schema

    compare = [t for t in tools if t.name == "compare_documents"][0]
    assert "queries" in compare.args_schema
    assert "dimension" in compare.args_schema

    compliance = [t for t in tools if t.name == "check_compliance"][0]
    assert "query" in compliance.args_schema
    assert "industry" in compliance.args_schema


def test_create_mcp_tools():
    """快捷创建函数"""
    tools = create_mcp_tools(
        retrieval_server=None,
        comparison_server=None,
        compliance_server=None,
    )
    assert len(tools) == 3


if __name__ == "__main__":
    test_mcp_tool_client_init()
    test_mcp_tool_descriptions()
    test_mcp_tool_has_args()
    test_create_mcp_tools()
    print("✅ 所有测试通过！")
