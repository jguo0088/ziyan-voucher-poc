# -*- coding: utf-8 -*-
"""DeepSeek 异常归因（步骤6-7）。

控制原则：LLM 只输出交易性质判断、归因、建议、复核意见，**不生成金额、不创造科目**。
"""
from __future__ import annotations
import json
import requests

SYSTEM = """你是资深财务审单与制单专家，服务于零售连锁门店（紫燕·卤味）的自动制单 POC。
给你若干「异常项」，请逐项专业分析。

严格要求：
1. 绝不生成任何金额，绝不创造科目——金额与科目由程序确定，你只做判断与建议。
2. 结合零售门店业务（多渠道收款、平台手续费、外卖暂估、储值卡、折扣净额法）给出专业归因。
3. 严格只输出 JSON 数组，不要 markdown 代码块、不要多余文字。每个元素字段：
   异常项 / 性质判断 / 可能原因 / 建议处理 / 是否需人工复核 / 需补充资料。"""


def _clean(s: str) -> str:
    s = s.strip()
    for p in ("```json", "```JSON", "```"):
        if s.startswith(p):
            s = s[len(p):]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


CHAT_SYSTEM = """你是紫燕门店财务制单助手，服务零售连锁门店的自动制单 POC。
请基于下面提供的【当前制单数据】回答用户问题，像资深财务/审计那样解释、分析、提示风险。

严格要求：
1. 只基于提供的真实数据回答，绝不编造金额、不虚构科目、不修改凭证。
2. 数据中没有的信息，明确说明"当前数据未提供"，不要臆测具体数字。
3. 回答专业、简洁、有条理；涉及判断时说明依据。
"""


def chat_with_context(question: str, context_text: str, history: list[dict],
                      api_key: str, base_url: str, model: str, timeout: int = 60) -> str:
    """对话式财务助手：基于当前制单数据回答。只解释/分析，不碰金额科目。"""
    if not api_key:
        return "（未配置 DeepSeek API Key，无法对话。）"
    messages = [{"role": "system", "content": CHAT_SYSTEM + "\n【当前制单数据】\n" + context_text}]
    messages += history[-8:]  # 仅保留最近若干轮，控制 token
    messages.append({"role": "user", "content": question})
    r = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 800},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


RULE_SYSTEM = """你是资深财务规则分析师。下面是某零售连锁门店（紫燕·卤味）历史凭证的统计结果
（科目使用频次、高频摘要、收入凭证借贷方向）。请像向财务汇报那样，用自然语言归纳该门店的记账逻辑与规则草案。

严格要求：
1. 只基于提供的统计事实归纳，不编造统计中未出现的科目，不编造任何金额。
2. 分点说明：收入确认、折扣处理、成本结转、外卖、税金等的记账规则（仅就统计中体现的）。
3. 末尾加一句"以上为 AI 依据历史账归纳的规则草案，需财务确认"。
4. 简洁专业，纯文本，不要 markdown 代码块。"""


def summarize_rules(stats_text: str, api_key: str, base_url: str,
                    model: str, timeout: int = 60) -> str:
    """大模型语义归纳：把规则学习的统计结果归纳为自然语言记账逻辑。"""
    if not api_key:
        return "（未配置 DeepSeek API Key，无法归纳。）"
    r = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "system", "content": RULE_SYSTEM},
                           {"role": "user", "content": "历史凭证统计：\n" + stats_text}],
              "temperature": 0.3, "max_tokens": 900},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def analyze_anomalies(anomalies: list[dict], api_key: str, base_url: str,
                      model: str, timeout: int = 60) -> tuple[list[dict], str]:
    """对异常项列表调用 DeepSeek，返回（结构化结果, 原始文本用于审计留痕）。"""
    if not api_key:
        return [{"异常项": "未配置 API Key", "性质判断": "-", "可能原因": "缺少 DEEPSEEK_API_KEY",
                 "建议处理": "配置后重试", "是否需人工复核": "是", "需补充资料": "API Key"}], ""
    user = "异常项列表：\n" + json.dumps(anomalies, ensure_ascii=False, indent=2)
    r = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": user}],
              "temperature": 0.2, "max_tokens": 1600},
        timeout=timeout,
    )
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(_clean(raw))
        if isinstance(parsed, dict):
            parsed = [parsed]
    except Exception:
        parsed = [{"异常项": "（LLM 输出解析失败）", "性质判断": "-", "可能原因": raw[:300],
                   "建议处理": "人工复核", "是否需人工复核": "是", "需补充资料": "-"}]
    return parsed, raw
