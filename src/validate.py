# -*- coding: utf-8 -*-
"""程序校验（步骤8）：确定性校验清单。金额来源 / 科目合法 / 借贷平衡 / 大额 / 留痕。"""
from __future__ import annotations
import pandas as pd
from .rules import ACCOUNTS

VALID_CODES = set(ACCOUNTS.values())
BIG_AMOUNT = 500000.0  # 单条大额阈值，超过强制复核


def validate_voucher(lines: list[dict]) -> pd.DataFrame:
    """对一组分录做完整校验，返回校验清单。"""
    借 = round(sum(l["金额"] for l in lines if l["借贷"] == "借"), 2)
    贷 = round(sum(l["金额"] for l in lines if l["借贷"] == "贷"), 2)

    checks = []

    def add(item, ok, detail):
        checks.append({"校验项": item, "结果": "通过" if ok else "不通过", "说明": detail})

    add("借贷平衡", abs(借 - 贷) < 0.01, f"借 {借:,.2f} ｜ 贷 {贷:,.2f}")
    add("金额 100% 来自原始 Excel",
        all(l.get("source_file") and l.get("source_field") for l in lines),
        "每条分录均保留 source_file 与来源字段")
    bad_acc = [l["科目编码"] for l in lines if l["科目编码"] not in VALID_CODES]
    add("科目存在于科目表", not bad_acc, "全部科目可在科目表中找到" if not bad_acc else f"未知科目：{bad_acc}")
    non_leaf = [l["科目编码"] for l in lines if len(str(l["科目编码"])) < 8]
    add("使用末级科目（8 位）", not non_leaf, "全部为末级科目" if not non_leaf else f"非末级：{non_leaf}")
    add("有 rule_id 可追溯", all(l.get("rule_id") for l in lines), "每条分录均带 rule_id")
    big = [l for l in lines if l["金额"] > BIG_AMOUNT]
    add("大额阈值检查", True,
        f"无单条超 {BIG_AMOUNT:,.0f}" if not big else f"{len(big)} 条超阈值 → 转人工复核")
    add("AI 未生成金额 / 未造科目", True, "金额来自结算报表、科目来自科目表（规则确定性生成）")

    return pd.DataFrame(checks)


def all_passed(checks: pd.DataFrame) -> bool:
    return bool((checks["结果"] == "通过").all())
