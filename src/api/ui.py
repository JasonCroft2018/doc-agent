"""
Streamlit 网页界面。

用法：
    streamlit run src/api/ui.py

需要先启动 FastAPI 服务：
    python src/api/main.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import httpx

from src.config.settings import settings

API_BASE = f"http://localhost:{settings.API_PORT}"

st.set_page_config(
    page_title="DocAgent — 文档智能助手",
    page_icon="📄",
    layout="wide",
)

st.title("📄 DocAgent — 企业文档智能助手")
st.markdown("> 基于 LangGraph + MCP + RAG 的企业文档智能检索系统")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    api_url = st.text_input("API 地址", value=API_BASE)

    st.divider()
    st.header("📊 状态")
    try:
        resp = httpx.get(f"{api_url}/api/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            st.success(f"✅ 服务正常（{data['collection_size']} 条文档）")
        else:
            st.error("❌ 服务异常")
    except Exception:
        st.warning("⏳ 服务未连接")

    st.divider()
    st.caption("DocAgent v0.1.0 | Jason Croft")

# 主界面
tab1, tab2 = st.tabs(["💬 对话", "🔍 直接检索"])

with tab1:
    st.header("💬 智能对话")
    st.markdown("输入你的问题，Agent 会自动判断意图并检索相关文档。")

    # 初始化对话历史
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 来源"):
                    for s in msg["sources"]:
                        st.caption(f"📄 {s['title']}（{s['source']}）")

    # 输入框
    if prompt := st.chat_input("请输入你的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    resp = httpx.post(
                        f"{api_url}/api/chat",
                        json={"query": prompt, "thread_id": "streamlit"},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer", "无回复")
                        sources = data.get("sources", [])
                        intent = data.get("intent", "unknown")

                        st.markdown(f"*（意图: {intent}）*")
                        st.markdown(answer)

                        if sources:
                            with st.expander("📚 来源"):
                                for s in sources:
                                    st.caption(
                                        f"📄 {s['title']}（{s['source']}）"
                                    )

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                        })
                    else:
                        st.error(f"API 错误: {resp.status_code}")
                except Exception as e:
                    st.error(f"请求失败: {e}")

with tab2:
    st.header("🔍 直接检索")
    st.markdown("输入关键词，直接检索文档（不走 Agent 流程）。")

    query = st.text_input("搜索关键词", key="search_input")
    top_k = st.slider("返回结果数", 1, 20, 5)

    if query:
        with st.spinner("检索中..."):
            try:
                resp = httpx.post(
                    f"{api_url}/api/search",
                    json={"query": query, "top_k": top_k},
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])

                    st.info(f"找到 {data['total']} 条结果")

                    for i, r in enumerate(results, 1):
                        with st.expander(
                            f"[{i}] {r.get('title', '未知')} "
                            f"（{r.get('source', '未知')}）"
                            f"— 相关度: {r.get('score', 0):.2f}"
                        ):
                            st.text(r.get("content", "")[:500])
                else:
                    st.error(f"API 错误: {resp.status_code}")
            except Exception as e:
                st.error(f"请求失败: {e}")
