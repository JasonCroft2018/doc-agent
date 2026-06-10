"""
Trace 模块：LangFuse 优先，未配置时打印日志到终端。
"""

import logging
import asyncio
from functools import wraps
from typing import Any, Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)
_trace_logger = logging.getLogger("docagent.trace")

# 终端 Trace 输出格式
TRACE_FORMAT = "\n🔍 [Trace] {name} | {msg}"


class ConsoleTracer:
    """终端打印 Trace（LangFuse 未配置时使用）"""

    def __init__(self):
        self._spans = []

    def trace(self, name: str, session_id: str = "default", input_data: Any = None):
        tid = f"trace-{session_id}"
        print(TRACE_FORMAT.format(name=name, msg=f"🟢 START | session={session_id}"))
        if input_data:
            print(f"   Input: {str(input_data)[:200]}")
        return _ConsoleSpan(tid, name)

    def span(self, trace_id: str, name: str, input_data: Any = None):
        print(TRACE_FORMAT.format(name=name, msg=f"  ├─ SPAN | trace={trace_id}"))
        if input_data:
            print(f"   Input: {str(input_data)[:200]}")
        return _ConsoleSpan(trace_id, name)


class _ConsoleSpan:
    def __init__(self, trace_id: str, name: str):
        self.trace_id = trace_id
        self.name = name

    def end(self, output: Any = None, **kwargs):
        print(f"  └─ END   | {str(output)[:200] if output else 'ok'}")

    def update(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.end()


# 全局 Trace 实例
_tracer = None


def get_tracer():
    global _tracer
    if _tracer is not None:
        return _tracer

    # 优先使用 LangFuse
    if settings.LANGFUSE_SECRET_KEY:
        try:
            from langfuse import Langfuse
            lf = Langfuse(
                host=settings.LANGFUSE_HOST,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
            )
            # 包装 LangFuse 接口为统一 Tracer
            class LangfuseTracer:
                def trace(self, name, session_id="default", input_data=None):
                    return lf.trace(name=name, session_id=session_id, input=str(input_data)[:500] if input_data else None)
                def span(self, trace_id, name, input_data=None):
                    return lf.span(trace_id=trace_id, name=name, input=str(input_data)[:500] if input_data else None)
            _tracer = LangfuseTracer()
            logger.info(f"LangFuse Trace 已启用: {settings.LANGFUSE_HOST}")
            return _tracer
        except Exception as e:
            logger.warning(f"LangFuse 连接失败: {e}，降级到终端打印")

    # 降级：终端打印
    _tracer = ConsoleTracer()
    logger.info("Trace 使用终端打印模式")
    return _tracer


def trace_agent(thread_id: str = "default"):
    """装饰器：自动追踪 Agent 调用"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            t = tracer.trace("doc-agent", session_id=thread_id, input_data=str(args)[:200])
            try:
                result = await func(*args, **kwargs)
                t.end(output=str(result)[:200])
                return result
            except Exception as e:
                t.end(output=f"ERROR: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            t = tracer.trace("doc-agent", session_id=thread_id, input_data=str(args)[:200])
            try:
                result = func(*args, **kwargs)
                t.end(output=str(result)[:200])
                return result
            except Exception as e:
                t.end(output=f"ERROR: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
