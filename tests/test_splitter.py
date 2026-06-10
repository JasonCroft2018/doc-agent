"""语义切片器测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag.splitter import parse_markdown_structure, chunk_by_semantic_boundary


def test_parse_simple_heading():
    """解析简单标题"""
    text = "# Title\ncontent"
    blocks = parse_markdown_structure(text)
    assert len(blocks) == 1
    assert blocks[0]["title"] == "Title"
    assert "content" in blocks[0]["text"]


def test_parse_multi_headings():
    """解析多级标题"""
    text = """# L1
content1
## L2
content2
### L3
content3"""
    blocks = parse_markdown_structure(text)
    assert len(blocks) == 3
    assert blocks[0]["title"] == "L1"
    assert blocks[1]["title"] == "L2"
    assert blocks[2]["title"] == "L3"


def test_parse_hierarchy():
    """验证层级栈正确"""
    text = """# A
a
## B
b"""
    blocks = parse_markdown_structure(text)
    assert len(blocks[1]["hierarchy"]) == 2  # A + B


def test_chunk_small_text():
    """短文本不分块"""
    text = "# Hello\nsmall content"
    chunks = chunk_by_semantic_boundary(text, chunk_size=500)
    assert len(chunks) == 1
    assert "Hello" in chunks[0]


def test_chunk_large_text():
    """长文本分块"""
    text = "# A\n" + "hello world\n\n" * 50
    chunks = chunk_by_semantic_boundary(text, chunk_size=100)
    assert len(chunks) > 1


def test_chunk_with_hierarchy():
    """带层级的分块"""
    text = """# L1
content1
## L2
""" + "content2\n\n" * 20 + "### L3\ncontent3"
    chunks = chunk_by_semantic_boundary(text, chunk_size=100)
    for c in chunks:
        assert "#" in c  # 确保层级信息保留


if __name__ == "__main__":
    test_parse_simple_heading()
    test_parse_multi_headings()
    test_parse_hierarchy()
    test_chunk_small_text()
    test_chunk_large_text()
    test_chunk_with_hierarchy()
    print("✅ 所有测试通过！")
