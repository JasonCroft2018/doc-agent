"""
安全节点：Prompt Injection 检测 + 敏感信息脱敏。
"""

import re
from typing import Tuple

# Prompt Injection 关键词
INJECTION_PATTERNS = [
    r"忽略(?:之前|前面|以上|所有).*(?:指令|命令|要求|规则|设定)",
    r"ignore(?: all)? (?:previous|above|prior) (?:instructions|commands|prompts|rules)",
    r"forget (?:all )?(?:previous|above).*(?:instructions|rules)",
    r"(?:你是|you are).*(?:AI|机器人|助手|robot|assistant).*(?:告诉|reveal|泄露).*(?:真实|秘密|内部|truth|secret)",
    r"(?:请|帮我).*扮演.*(?:角色|role)",
    r"pretend.*(?:role|play|to be)",
    r"bypass.*(?:rule|restriction|guardrail|safety|filter)",
    r"绕过.*(?:规则|限制|安全|审核|过滤)",
    r"无视.*(?:规则|指令|设定)",
    r"disregard.*(?:rules|instructions|previous)",
]

# 敏感信息模式（从 settings.py 同步）
SENSITIVE_PATTERNS = [
    (r"\d{18}[\dXx]", "身份证号"),       # 身份证
    (r"1[3-9]\d{9}", "手机号"),           # 手机号
    (r"\d{6,}", "连续数字"),              # 6位以上数字
]


def detect_injection(text: str) -> Tuple[bool, str]:
    """
    检测 Prompt Injection。

    Returns:
        (是否检测到注入, 匹配到的模式描述)
    """
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"匹配到注入模式: {pattern[:30]}"
    return False, ""


def sanitize_output(text: str) -> str:
    """
    对输出内容进行脱敏处理。

    替换：
    - 身份证号 → 320***********1234
    - 手机号   → 138****1234
    """
    result = text
    for pattern, name in SENSITIVE_PATTERNS:
        # 身份证号：保留前3位和后4位
        if name == "身份证号":
            result = re.sub(r"(\d{3})\d{11}(\d{4})", r"\1***********\2", result)
        # 手机号：保留前3位和后4位  
        elif name == "手机号":
            result = re.sub(r"(1[3-9]\d)\d{4}(\d{4})", r"\1****\2", result)
        # 连续数字：替换为 ****
        elif name == "连续数字":
            result = re.sub(r"\b\d{8,}\b", "****", result)
    return result


def run_security_check(text: str) -> Tuple[bool, str, str]:
    """
    完整安全检查：注入检测 + 脱敏。

    Returns:
        (是否安全, 脱敏后的文本, 注入警告信息)
    """
    # 1. 注入检测
    detected, warning = detect_injection(text)
    if detected:
        return False, text, f"⚠️ 检测到 Prompt Injection: {warning}"

    # 2. 输出脱敏
    sanitized = sanitize_output(text)

    return True, sanitized, ""
