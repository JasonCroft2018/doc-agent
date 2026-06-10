"""
Trace 日志存储：将 Trace 写入环形缓冲区，通过 API 提供最新记录。
"""

import os
from typing import List

TRACE_LOG_PATH = os.path.join(os.path.dirname(__file__), "../../data/trace_log.txt")
MAX_LINES = 100


def write_trace(line: str):
    """写入一条 Trace 日志"""
    os.makedirs(os.path.dirname(TRACE_LOG_PATH), exist_ok=True)
    with open(TRACE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    # 保持文件不超过 MAX_LINES
    _trim_log()


def get_latest_trace() -> List[str]:
    """获取最近的 Trace 日志"""
    if not os.path.exists(TRACE_LOG_PATH):
        return ["暂无 Trace 日志"]
    with open(TRACE_LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [l.strip() for l in lines[-30:]]


def _trim_log():
    """保留最后 MAX_LINES 行"""
    if not os.path.exists(TRACE_LOG_PATH):
        return
    with open(TRACE_LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if len(lines) > MAX_LINES:
        with open(TRACE_LOG_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines[-MAX_LINES:])
