#!/bin/bash
# DocAgent 一键启动脚本
cd "$(dirname "$0")"

echo "=========================================="
echo "  DocAgent 启动中..."
echo "=========================================="

# 杀掉旧进程
lsof -ti :8765 2>/dev/null | xargs kill -9 2>/dev/null
sleep 2

# 启动
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8765 --log-level warning &
PID=$!
sleep 4

echo ""
echo "  ✅ 服务已启动 (PID: $PID)"
echo "  🌐 http://localhost:8765"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "=========================================="

wait $PID
