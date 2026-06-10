"""
合规规则引擎：加载 YAML 规则 → 匹配文档 → 输出风险报告。
"""

import os
import re
import yaml
from typing import List, Dict

RULES_PATH = os.path.join(os.path.dirname(__file__), "../../rules/compliance.yaml")


def load_rules() -> List[Dict]:
    """加载合规规则"""
    if not os.path.exists(RULES_PATH):
        return []
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])


def check_compliance(text: str) -> List[Dict]:
    """
    对文本执行合规检查。

    Args:
        text: 需要检查的文本（合同/文档内容）

    Returns:
        风险报告列表
    """
    rules = load_rules()
    findings = []

    for rule in rules:
        keywords = rule.get("keywords", [])
        check_type = rule.get("check_type", "present")  # present 或 missing
        found = any(kw.lower() in text.lower() for kw in keywords)

        if check_type == "missing":
            # 关键词缺失 → 报风险
            if not found:
                findings.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "risk_level": rule.get("risk_level", "medium"),
                    "description": rule.get("description", ""),
                    "detail": f"未找到相关条款: {', '.join(keywords)}",
                })
        else:
            # 关键词存在 → 进一步检查
            if found:
                pattern = rule.get("pattern")
                threshold = rule.get("threshold")
                detail = None

                if pattern and threshold:
                    # 提取数值并比较阈值
                    matches = re.findall(pattern, text)
                    for m in matches:
                        nums = re.findall(r"\d+", str(m))
                        for n in nums:
                            if int(n) > threshold:
                                detail = f"检测到 {rule['name']}: {n} > 阈值 {threshold}"

                if detail:
                    findings.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "risk_level": rule.get("risk_level", "medium"),
                        "description": rule.get("description", ""),
                        "detail": detail,
                    })

    return findings


def format_report(findings: List[Dict]) -> str:
    """格式化风险报告为可读文本"""
    if not findings:
        return "✅ 未发现合规风险。"

    report = [f"⚠️ 发现 {len(findings)} 个合规风险点：\n"]
    levels = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}

    for i, f in enumerate(findings, 1):
        level = levels.get(f.get("risk_level", "medium"), "🟡 中")
        report.append(f"{i}. {level} | {f['name']}")
        report.append(f"   描述: {f['description']}")
        report.append(f"   详情: {f['detail']}\n")

    return "\n".join(report)
