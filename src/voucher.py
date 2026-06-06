# -*- coding: utf-8 -*-
"""制单：把月度归集 → 会计分录草稿（每条分录留 source / rule_id）。"""
from __future__ import annotations
import os
from .rules import ACCOUNTS, TAX_RATE, RULES

SOURCE_FILE = "5.01紫燕直营店结算报表.xlsx"


def _line(zhaiyao, acct_name, dc, amount, rule_id, source_field):
    """构造一条分录。dc: '借'/'贷'。"""
    return {
        "凭证摘要": zhaiyao,
        "科目编码": ACCOUNTS[acct_name],
        "科目名称": acct_name,
        "借贷": dc,
        "金额": round(amount, 2),
        "rule_id": rule_id,
        "source_file": SOURCE_FILE,
        "source_field": source_field,  # 金额来源列（可追溯）
    }


def gen_revenue_voucher(ym: str, row: dict) -> list[dict]:
    """生成某月直营店『确认收入及结转成本』凭证。

    row: monthly_summary 的一行（含 门店收款小计 / 工厂配送金额 等）。
    """
    收款小计 = float(row.get("门店收款小计", 0) or 0)
    成本 = float(row.get("工厂配送金额", 0) or 0)  # 成本候选源：工厂配送金额（待验证/待接成本系统）

    收入 = round(收款小计 / (1 + TAX_RATE), 2)
    销项税 = round(收款小计 - 收入, 2)
    zy = f"{ym} 直营店确认收入及结转成本-虬长"

    lines = [
        _line(zy, "应收账款-直营店", "借", 收款小计, "R-REV-DIRECT", "门店收款小计"),
        _line(zy, "主营业务收入-直营店", "贷", 收入, "R-REV-DIRECT", "门店收款小计÷1.13"),
        _line(zy, "销项税13", "贷", 销项税, "R-REV-DIRECT", "门店收款小计×13%/1.13"),
    ]
    if 成本 > 0:
        lines += [
            _line(zy, "主营业务成本-直营店", "借", 成本, "R-COST-DIRECT", "工厂配送金额"),
            _line(zy, "发出商品", "贷", 成本, "R-COST-DIRECT", "工厂配送金额"),
        ]
    return lines


# 折扣来源渠道（券 / 储值 / 优惠，键对齐 io_settlement.CHANNEL_GROUPS）
DISCOUNT_SRC_GROUPS = ["团购券类", "券/折扣类", "储值/会员", "折扣调整", "其它支付"]


def gen_discount_voucher(ym: str, row: dict) -> list[dict]:
    """生成折扣调整凭证（净额法冲减）。

    折扣口径 = 券/储值/优惠各渠道合计（近似，与真实凭证差约 0.1%，待财务确认）。
    方向参照真实凭证 0101062：借主营收入-折扣 + 借销项税 / 贷应收账款-直营店。
    """
    含税折扣 = sum(float(row.get(g, 0) or 0) for g in DISCOUNT_SRC_GROUPS)
    if 含税折扣 <= 0.01:
        return []
    不含税 = round(含税折扣 / (1 + TAX_RATE), 2)
    销项税 = round(含税折扣 - 不含税, 2)
    zy = f"{ym} 折扣调整-虬长（净额法冲减）"
    return [
        _line(zy, "主营业务收入-折扣", "借", 不含税, "R-DISCOUNT", "券/储值/优惠合计÷1.13"),
        _line(zy, "销项税13", "借", 销项税, "R-DISCOUNT", "券/储值/优惠合计×13%/1.13"),
        _line(zy, "应收账款-直营店", "贷", 含税折扣, "R-DISCOUNT", "券/储值/优惠合计"),
    ]


def gen_takeaway_voucher(ym: str, row: dict) -> list[dict]:
    """生成外卖应收结转（暂估）凭证：把外卖部分应收从直营店重分类到外卖平台。

    方向参照序时账『应收账款-外卖平台』科目：借应收账款-外卖平台 / 贷应收账款-直营店。
    暂估按结算报表外卖金额；拿到平台账单后，差异（抽佣）再计平台服务费。
    """
    外卖 = round(float(row.get("外卖-美团", 0) or 0) + float(row.get("外卖-饿了么", 0) or 0), 2)
    if 外卖 <= 0.01:
        return []
    zy = f"{ym} 外卖应收结转-虬长（暂估）"
    return [
        _line(zy, "应收账款-外卖平台", "借", 外卖, "R-TAKEAWAY", "外卖-美团+饿了么"),
        _line(zy, "应收账款-直营店", "贷", 外卖, "R-TAKEAWAY", "外卖-美团+饿了么"),
    ]


def check_balance(lines: list[dict]) -> tuple[float, float, bool]:
    """借贷平衡校验（确定性）。"""
    借 = round(sum(l["金额"] for l in lines if l["借贷"] == "借"), 2)
    贷 = round(sum(l["金额"] for l in lines if l["借贷"] == "贷"), 2)
    return 借, 贷, abs(借 - 贷) < 0.01
