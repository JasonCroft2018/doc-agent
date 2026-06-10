"""
LLM-as-Judge 评测脚本。

用法：
    python3 tests/evaluation/run_eval.py              # 运行全部测试
    python3 tests/evaluation/run_eval.py --quiet       # 只输出汇总
    python3 tests/evaluation/run_eval.py --case TC-001 # 单条测试
"""

import json
import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

API_BASE = "http://127.0.0.1:8765"
SUITE_PATH = os.path.join(os.path.dirname(__file__), "test_suite.json")

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"

# 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def load_suite():
    with open(SUITE_PATH) as f:
        return json.load(f)


def run_test_case(tc):
    """运行单条测试用例"""
    query = tc["query"]
    
    # 跳过空查询（前端会拦截）
    if not query.strip():
        return {"status": SKIP, "reason": "空查询被前端拦截"}

    try:
        resp = requests.post(
            f"{API_BASE}/api/chat",
            json={"query": query, "thread_id": "eval"},
            timeout=60,
        )
        if resp.status_code != 200:
            return {"status": FAIL, "reason": f"HTTP {resp.status_code}"}

        data = resp.json()
        intent = data.get("intent", "")
        answer = data.get("answer", "")

        # 检查意图
        expected_intent = tc["expected_intent"]
        intent_ok = intent == expected_intent

        # 检查关键词
        keywords = tc.get("expected_keywords", [])
        keyword_ok = True
        missing_kw = []
        if keywords:
            for kw in keywords:
                if kw.lower() not in answer.lower():
                    keyword_ok = False
                    missing_kw.append(kw)

        # 评分
        score = 0
        if intent_ok:
            score += 0.6
        if keyword_ok:
            score += 0.4

        if score >= 0.8:
            status = PASS
        elif score >= 0.4:
            status = SKIP
        else:
            status = FAIL

        return {
            "status": status,
            "score": round(score, 2),
            "intent": intent,
            "intent_ok": intent_ok,
            "keyword_ok": keyword_ok,
            "missing_keywords": missing_kw,
            "answer_preview": answer[:80],
        }

    except requests.exceptions.ConnectionError:
        return {"status": FAIL, "reason": f"无法连接 API ({API_BASE})"}
    except Exception as e:
        return {"status": FAIL, "reason": str(e)}


def main():
    suite = load_suite()
    test_cases = suite["test_cases"]
    threshold = suite["threshold_pass_rate"]

    # 过滤单条
    if "--case" in sys.argv:
        idx = sys.argv.index("--case") + 1
        case_id = sys.argv[idx]
        test_cases = [tc for tc in test_cases if tc["id"] == case_id]
        if not test_cases:
            print(f"未找到用例: {case_id}")
            sys.exit(1)

    quiet = "--quiet" in sys.argv

    total = len(test_cases)
    passed = 0
    failed = 0
    skipped = 0

    if not quiet:
        print(f"\n{'='*60}")
        print(f"  DocAgent 评测 — {suite['description']}")
        print(f"  版本: {suite['version']}  |  通过阈值: {threshold*100}%")
        print(f"{'='*60}\n")

    for tc in test_cases:
        result = run_test_case(tc)

        if result["status"] == PASS:
            passed += 1
        elif result["status"] == FAIL:
            failed += 1
        else:
            skipped += 1

        if not quiet:
            color = GREEN if result["status"] == PASS else (RED if result["status"] == FAIL else YELLOW)
            print(f"  {color}{result['status']}{RESET} {tc['id']} | {tc['description']}")
            
            if result["status"] == PASS:
                print(f"     意图: {result.get('intent', '?')}  |  分数: {result.get('score', 0)}")
            elif result["status"] == FAIL:
                reason = result.get("reason", result.get("answer_preview", "未知"))
                print(f"     {RED}原因: {reason}{RESET}")
            else:
                print(f"     {YELLOW}部分匹配 — {result.get('intent', '?')}{RESET}")

    # 汇总
    pass_rate = passed / total if total > 0 else 0
    gate = pass_rate >= threshold

    print(f"\n{'='*60}")
    print(f"  汇总: {PASS} {passed}  |  {FAIL} {failed}  |  {SKIP} {skipped}  |  总计 {total}")
    print(f"  通过率: {pass_rate*100:.0f}%  |  阈值: {threshold*100:.0f}%")
    
    if gate:
        print(f"  {GREEN}✅ 门禁通过 — 可以发布{RESET}")
    else:
        print(f"  {RED}❌ 门禁未通过 — 修复后重试{RESET}")
    print(f"{'='*60}\n")

    return 0 if gate else 1


if __name__ == "__main__":
    # 先检查 API 是否在线
    try:
        requests.get(f"{API_BASE}/api/health", timeout=5)
    except:
        print(f"{RED}❌ API 未运行，请先启动: bash start.sh{RESET}")
        sys.exit(1)
    sys.exit(main())
