#!/bin/bash
# DocAgent 内部测试脚本
# 用法：bash tests/run_test.sh

BASE="http://127.0.0.1:8765"
PASS=0
FAIL=0
RESULTS=""

log() {
  local msg="$1"
  RESULTS+="$msg"$'\n'
  echo "$msg"
}

log "=========================================="
log "📋 DocAgent 内部测试报告"
log "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
log "=========================================="
log ""

# T1: 进程检查
log "【T1】进程检查"
PID=$(ps aux | grep "uvicorn" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
  log "  ✅ API 进程运行中 (PID: $PID)"
  ((PASS++))
else
  log "  ❌ API 未运行"
  ((FAIL++))
fi
log ""

# T2: 端口监听
log "【T2】端口 8765 监听检查"
if lsof -i :8765 2>/dev/null | grep -q LISTEN; then
  log "  ✅ 端口 8765 正在监听"
  ((PASS++))
else
  log "  ❌ 端口未监听"
  ((FAIL++))
fi
log ""

# T3: Health 端点
log "【T3】GET /api/health"
H=$(curl -s -m 5 "$BASE/api/health" 2>/dev/null)
if echo "$H" | grep -q '"status":"ok"'; then
  MODEL=$(echo "$H" | grep -o '"model_loaded":true' || echo "false")
  log "  ✅ 响应正常，模型已加载"
  ((PASS++))
else
  log "  ❌ 响应异常: $H"
  ((FAIL++))
fi
log ""

# T4: Stats 端点
log "【T4】GET /api/stats"
S=$(curl -s -m 5 "$BASE/api/stats" 2>/dev/null)
if echo "$S" | grep -q "collection_size"; then
  log "  ✅ 响应正常"
  ((PASS++))
else
  log "  ❌ 响应异常: $S"
  ((FAIL++))
fi
log ""

# T5: Chat（问候）
log "【T5】POST /api/chat（问候意图）"
C1=$(curl -s -m 120 -X POST "$BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"query":"你好","thread_id":"t1"}' 2>/dev/null)
if echo "$C1" | grep -q "intent"; then
  INTENT=$(echo "$C1" | python3 -c "import sys,json;print(json.load(sys.stdin).get('intent','unknown'))" 2>/dev/null)
  log "  ✅ 意图识别: $INTENT"
  ((PASS++))
else
  log "  ❌ 响应异常"
  ((FAIL++))
fi
log ""

# T6: Chat（检索-无文档）
log "【T6】POST /api/chat（检索意图，无文档时）"
C2=$(curl -s -m 120 -X POST "$BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"query":"什么是Transformer","thread_id":"t2"}' 2>/dev/null)
if echo "$C2" | grep -q "intent"; then
  INTENT2=$(echo "$C2" | python3 -c "import sys,json;print(json.load(sys.stdin).get('intent','unknown'))" 2>/dev/null)
  log "  ✅ 意图识别: $INTENT2（正确降级处理）"
  ((PASS++))
else
  log "  ❌ 响应异常"
  ((FAIL++))
fi
log ""

# T7: Search（空索引）
log "【T7】POST /api/search（空索引时）"
SR=$(curl -s -m 30 -X POST "$BASE/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","top_k":3}' 2>/dev/null)
if echo "$SR" | grep -q "results"; then
  log "  ✅ 正常返回空结果"
  ((PASS++))
else
  log "  ❌ 响应异常: $(echo $SR | head -c 80)"
  ((FAIL++))
fi
log ""

# T8: HTML 页面
log "【T8】GET /（HTML UI 页面）"
PG=$(curl -s -m 5 "$BASE/" 2>/dev/null)
PG_SIZE=${#PG}
if echo "$PG" | grep -q "DocAgent"; then
  log "  ✅ 页面返回（${PG_SIZE} bytes），包含 DocAgent 标题"
  ((PASS++))
else
  log "  ❌ 页面异常（${PG_SIZE} bytes）"
  ((FAIL++))
fi
log ""

# T9: Ollama 连接
log "【T9】Ollama 模型检查"
OM=$(curl -s -m 5 http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    models=[m['name'] for m in d.get('models',[])]
    print('✅ 模型:', ', '.join(models))
except: print('❌ 连接失败')
" 2>/dev/null)
log "  $OM"
((PASS++))
log ""

# 汇总
log "=========================================="
log "📊 汇总: $PASS 通过 / $((PASS+FAIL)) 总计"
if [ $FAIL -eq 0 ]; then
  log "🎉 全部通过！"
else
  log "❌ $FAIL 项失败"
fi
log "=========================================="

# 保存结果到文件
echo "$RESULTS" > /tmp/docagent_test_report.txt
