"""
语义切片器：按 Markdown 标题层级和段落边界分割文档。
比固定长度切片更准确保留语义完整性。

对比课题16：课题16 按 500 字符硬切，无视文档结构。
本实现按标题层级 + 段落边界切，保留上下文的语义完整性。
"""

import re
from typing import List, Dict, Optional


def parse_markdown_structure(text: str) -> List[Dict]:
    """
    将 Markdown 文本解析为结构化块。

    返回：
    [
        {
            "title": "Self-Attention",
            "level": 2,
            "hierarchy": [{"title": "Transformer 原理", "level": 1}],
            "text": "注意力机制的核心是 QKV 计算..."
        },
        ...
    ]
    """
    lines = text.split("\n")
    blocks = []
    current_section: Dict = {"title": "", "level": 0, "content": []}
    current_hierarchy: List[Dict] = []  # 标题栈

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # 保存上一个块
            if current_section["content"]:
                content_text = "\n".join(current_section["content"]).strip()
                if content_text:
                    blocks.append({
                        "title": current_section["title"],
                        "level": current_section["level"],
                        "hierarchy": list(current_hierarchy),
                        "text": content_text,
                    })

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            # 更新层级栈：弹出同级或更深的标题
            while current_hierarchy and current_hierarchy[-1]["level"] >= level:
                current_hierarchy.pop()
            current_hierarchy.append({"title": title, "level": level})

            current_section = {"title": title, "level": level, "content": []}
        else:
            current_section["content"].append(line)

    # 最后一个块
    if current_section["content"]:
        content_text = "\n".join(current_section["content"]).strip()
        if content_text:
            blocks.append({
                "title": current_section["title"],
                "level": current_section["level"],
                "hierarchy": list(current_hierarchy),
                "text": content_text,
            })

    return blocks


def chunk_by_semantic_boundary(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> List[str]:
    """
    按语义边界切片，保留标题上下文。

    策略：
    1. 先按 Markdown 标题层级解析为结构化块
    2. 每个块带上层级标题作为上下文前缀
    3. 块小于 chunk_size 直接合并
    4. 大块按段落边界再切
    5. overlap 保留最后一段内容

    Args:
        text: Markdown 文本
        chunk_size: 每块最大字符数
        overlap: 块间重叠字符数

    Returns:
        切分后的文本块列表
    """
    blocks = parse_markdown_structure(text)
    chunks = []

    for block in blocks:
        block_text = block["text"]
        if not block_text.strip():
            continue

        # 构建上下文前缀（层级标题链）
        prefix_lines = []
        for h in block["hierarchy"]:
            prefix_lines.append(f"{'#' * h['level']} {h['title']}")
        prefix = "\n".join(prefix_lines) + "\n"

        # 如果块本身小于 chunk_size，直接使用
        if len(block_text) + len(prefix) <= chunk_size:
            chunks.append(prefix + block_text)
            continue

        # 大块按段落边界再切
        paragraphs = [p.strip() for p in block_text.split("\n\n") if p.strip()]
        current_chunk = prefix
        last_para = ""

        for para in paragraphs:
            needed = len(current_chunk) + len(para) + 1
            if needed > chunk_size and current_chunk != prefix:
                # 当前块已满，保存
                chunks.append(current_chunk.strip())
                # overlap：从上一个 chunk 的最后一段开始
                current_chunk = prefix + last_para + "\n\n" + para
            else:
                current_chunk += "\n\n" + para
            last_para = para

        if current_chunk.strip() != prefix.strip():
            chunks.append(current_chunk.strip())

    return chunks
