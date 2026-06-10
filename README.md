# 📄 DocAgent — 企业文档智能助手

[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> 一个基于 LangGraph + MCP + RAG 的企业文档智能助手。  
> 支持多格式文档检索、多文档对比、合规检查，全部本地部署。

---

## 🚀 快速开始

### 前置条件

- Python 3.9+
- [Ollama](https://ollama.com) 已安装，并拉取了以下模型：
  ```bash
  ollama pull deepseek-r1:14b   # LLM（也可用 qwen2.5:3b）
  ollama pull bge-m3            # Embedding 模型
  ```

### 安装与启动

```bash
# 1. 克隆
git clone https://github.com/your-username/doc-agent.git
cd doc-agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 按需修改 .env 中的 LLM_MODEL（可选 deepseek-r1:14b 或 qwen2.5:3b）

# 4. 启动
bash start.sh
# 或：python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8765

# 5. 打开浏览器
# http://localhost:8765
```

---

## 🏗️ 架构

```
用户 → FastAPI + HTML UI
         │
    LangGraph Agent（意图识别 → 路由 → 生成）
         │
    MCP 协议（标准化工具调用）
         │
    RAG 管道（语义切片 → 混合检索 → 重排）
         │
    向量库 ChromaDB + BM25 关键词索引
```

### 技术栈

| 组件 | 选型 |
|:----|:----|
| Agent 框架 | LangGraph（状态图） |
| LLM | deepseek-r1:14b / qwen2.5:3b（Ollama 本地） |
| Embedding | bge-m3（Ollama 本地） |
| 检索策略 | 向量 + BM25 混合检索 + RRF 融合 |
| API 框架 | FastAPI |
| 向量库 | ChromaDB |
| 容器化 | Docker + docker-compose |

---

## 📁 项目结构

```
doc-agent/
├── src/
│   ├── agent/          # LangGraph Agent（意图识别 / 检索 / 输出）
│   ├── rag/            # RAG 管道（切片器 / 检索器 / BM25 / Query改写）
│   ├── mcp/            # MCP 协议（Server + Client 包装）
│   └── api/            # FastAPI 服务 + HTML UI
├── tests/              # 24 个单元测试 + 9 项集成测试
├── docs/               # 架构说明
├── scripts/            # 索引脚本
├── AGENT_SKILL.md      # 项目交付方法论
├── TEST_SKILL.md       # 测试体系手册
├── .env.example        # 环境变量模板
└── Dockerfile
```

---

## 🔒 安全

- 所有敏感信息通过环境变量注入（`.env`），不硬编码
- 数据目录 `data/` 已加入 `.gitignore`，不提交到仓库
- 全部本地部署，不依赖任何第三方 API 服务
- MIT License

---

## 🧪 测试

```bash
# 单元测试（24 个用例）
python3 tests/test_splitter.py
python3 tests/test_retriever.py
python3 tests/test_agent.py
python3 tests/test_mcp.py
python3 tests/test_api.py

# 集成测试（9 项）
bash tests/run_test.sh
```

---

## 🗺️ 开发路线

| Phase | 内容 | 状态 |
|:----|:----|:----:|
| 1 | RAG 管道（语义切片 + 混合检索 + 重排） | ✅ |
| 2 | LangGraph Agent 核心 | ✅ |
| 3 | MCP 协议集成 | ✅ |
| 4 | FastAPI 服务化 + HTML UI + Docker | ✅ |
| 5 | 可观测性（LangFuse）+ 评测体系 | ⏳ |
| 6 | 安全加固 + 合规规则引擎 | ⏳ |

---

> **作者**: Jason Croft | **License**: MIT
