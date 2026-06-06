# -*- coding: utf-8 -*-
"""生成 POC 三份输出：凭证草稿 / 人工复核清单 / AI 审计留痕。"""
from __future__ import annotations
import os
from datetime import datetime
import pandas as pd


def make_batch_id() -> str:
    return "ZY" + datetime.now().strftime("%Y%m%d%H%M%S")


def build_voucher_draft(batch_id: str, ym: str, lines: list[dict], need_review: bool, review_reason: str) -> pd.DataFrame:
    rows = []
    for l in lines:
        rows.append({
            "批次号": batch_id,
            "凭证日期": f"{ym}-月末",
            "凭证摘要": l["凭证摘要"],
            "科目编码": l["科目编码"],
            "科目名称": l["科目名称"],
            "借贷": l["借贷"],
            "金额": l["金额"],
            "rule_id": l["rule_id"],
            "数据来源文件": l["source_file"],
            "来源字段": l["source_field"],
            "是否需复核": "是" if need_review else "否",
            "复核原因": review_reason if need_review else "",
        })
    return pd.DataFrame(rows)


def build_manual_review(batch_id: str, items: list[dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["批次号", "事项", "异常原因", "需补充资料", "复核意见", "最终确认"])
    return pd.DataFrame([{"批次号": batch_id, **it} for it in items])


def build_audit_log(batch_id: str, logs: list[dict]) -> pd.DataFrame:
    if not logs:
        return pd.DataFrame(columns=["批次号", "调用场景", "输入摘要", "AI输出", "模型版本", "提示词版本", "规则版本", "调用时间"])
    return pd.DataFrame([{"批次号": batch_id, **lg} for lg in logs])


def build_import_template(batch_id: str, ym: str, lines: list[dict]) -> pd.DataFrame:
    """生成符合财务系统导入格式的凭证模板（一借一贷一行，借/贷分列）。"""
    rows = []
    for i, l in enumerate(lines, 1):
        rows.append({
            "凭证日期": f"{ym}-月末",
            "凭证字": "记",
            "分录号": i,
            "摘要": l["凭证摘要"],
            "科目编码": l["科目编码"],
            "科目名称": l["科目名称"],
            "借方金额": l["金额"] if l["借贷"] == "借" else 0,
            "贷方金额": l["金额"] if l["借贷"] == "贷" else 0,
            "制单人": "AI制单·待财务复核",
            "批次号": batch_id,
        })
    return pd.DataFrame(rows)


def write_all(out_dir: str, batch_id: str, draft: pd.DataFrame, review: pd.DataFrame, audit: pd.DataFrame) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "voucher_draft": os.path.join(out_dir, f"{batch_id}_voucher_draft.xlsx"),
        "manual_review": os.path.join(out_dir, f"{batch_id}_manual_review.xlsx"),
        "ai_audit_log": os.path.join(out_dir, f"{batch_id}_ai_audit_log.xlsx"),
    }
    draft.to_excel(paths["voucher_draft"], index=False)
    review.to_excel(paths["manual_review"], index=False)
    audit.to_excel(paths["ai_audit_log"], index=False)
    return paths
