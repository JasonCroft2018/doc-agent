"""
LangFuse Trace 集成。

提供装饰器和上下文管理器，让 Agent 的每次调用自动打 span。
"""

import logging
import os
from functools import wraps
from typing import Optional, Any

from src.config.settings import settings

logger = logging.getLogger(__name__)

# 全局 LangFuse 实例（延迟初始化）
_langfuse = None


def get_langfuse():
    """获取 LangFuse 单例"""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    # 如果没有配置密钥，返回 None（不启用 trace）
    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.info("LangFuse 未配置（LANGFUSE_SECRET_KEY 为空），Trace 功能未启用")
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            host=settings.LANGFUSE_HOST,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
        )
        logger.info(f"LangFuse 已连接: {settings.LANGFUSE_HOST}")
    except Exception as e:
        logger.warning(f"LangFuse 连接失败: {e}")
        return None

    return _langfuse


def trace_agent(thread_id: str = "default"):
    """
    装饰器：自动为 Agent 调用创建 trace。

    用法：
        @trace_agent(thread_id="user-123")
        def run_agent(query):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            lf = get_langfuse()
            if lf is None:
                return await func(*args, **kwargs)

            trace = lf.trace(
                name="doc-agent",
                session_id=thread_id,
                input=str(args),
            )
            try:
                result = await func(*args, **kwargs)
                trace.update(output=str(result)[:1000])
                return result
            except Exception as e:
                trace.update(metadata={"error": str(e)})
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            lf = get_langfuse()
            if lf is None:
                return func(*args, **kwargs)

            trace = lf.trace(
                name="doc-agent",
                session_id=thread_id,
                input=str(args),
            )
            try:
                result = func(*args, **kwargs)
                trace.update(output=str(result)[:1000])
                return result
            except Exception as e:
                trace.update(metadata={"error": str(e)})
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def create_span(trace_id: str, name: str, input_data: Any = None):
    """
    在已有 trace 下创建 span。

    用法：
        span = create_span(trace_id, "llm_call", prompt)
        span.end(output=response)
    """
    lf = get_langfuse()
    if lf is None:
        return _NullSpan()

    try:
        return lf.span(
            trace_id=trace_id,
            name=name,
            input=str(input_data)[:500] if input_data else None,
        )
    except Exception:
        return _NullSpan()


class _NullSpan:
    """当 LangFuse 未配置时使用的空对象，避免到处判空"""
    def end(self, **kwargs): pass
    def update(self, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


# 解决 async 检测的 import
import asyncio
