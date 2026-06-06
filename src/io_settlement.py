# -*- coding: utf-8 -*-
"""读取紫燕直营店结算报表（多级表头），归集到门店 × 月度 × 渠道。

结算报表结构（见 scripts/inspect_settlement.py 探查）：
- 第 0 行：标题
- 第 1 行：一级表头（合并单元格，需前向填充）
- 第 2 行：二级表头
- 第 3 行起：数据，共 64 列
"""
from __future__ import annotations
import warnings
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def _to_float(v) -> float:
    """金额安全转 float：空/异常 → 0.0。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    s = str(v).strip().replace(",", "")
    if s == "" or s.lower() == "nan":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_settlement(path: str) -> pd.DataFrame:
    """读结算报表 → 规整 DataFrame。列名取二级表头，二级为空时取一级。"""
    raw = pd.read_excel(path, header=None, dtype=str)
    lv1 = raw.iloc[1].ffill()
    lv2 = raw.iloc[2]
    cols = []
    for i in range(raw.shape[1]):
        b = "" if pd.isna(lv2[i]) else str(lv2[i]).strip()
        a = "" if pd.isna(lv1[i]) else str(lv1[i]).strip()
        cols.append(b if b else a)
    df = raw.iloc[3:].copy()
    df.columns = cols
    df = df[df["门店编码"].notna() & (df["门店编码"].astype(str).str.strip() != "")]
    df["报表日期"] = pd.to_datetime(df["报表日期"], errors="coerce")
    df = df[df["报表日期"].notna()]
    df["年月"] = df["报表日期"].dt.strftime("%Y-%m")
    return df


# 渠道分组：把 46 个收款列归并为业务可读的大类（用于制单/对账）
CHANNEL_GROUPS: dict[str, list[str]] = {
    "POS-支付宝(应收)": ["支付宝POS应收"],
    "POS-微信(应收)": ["微信POS应收"],
    "POS-银联翼支付等": ["银联钱包POS应收", "翼支付POS应收", "交行数字钱包POS应收"],
    "账户实收-支付宝": ["支付宝账户实收"],
    "账户实收-微信": ["微信账户实收"],
    "微信手续费": ["微信账户手续费"],
    "外卖-美团": ["美团外卖(原价)", "美团外卖(实收)", "美团外卖(万美人)"],
    "外卖-饿了么": ["饿了么(原价)", "饿了么(实收)", "饿了么(万美人)"],
    "外卖-京东到家": ["京东到家(原价)", "京东到家(实收)"],
    "外卖-抖音/紫燕": ["抖音外卖", "紫燕外卖(原价)", "紫燕外卖(实收)"],
    "自提-紫燕": ["紫燕自提(原价)", "紫燕自提(实收)"],
    "团购券类": ["美团团购", "美团券", "美团到店付", "糯米券", "口碑单品券", "口碑小票",
              "口碑点餐", "支付宝团购券", "支付宝团购券小票", "高德团购券", "抖音来客"],
    "券/折扣类": ["活动优惠券", "代金券（优惠券）", "异业电子券(提货券)", "异业券小票", "会员电子券"],
    "储值/会员": ["会员储值付", "紫燕储值卡消费", "瑞祥卡消费"],
    "现金": ["现金"],
    "其它支付": ["自助点餐", "试吃支付", "积分抵现"],
    "折扣调整": ["手工抹零", "门店促销金额"],
}


def monthly_summary(df: pd.DataFrame, store_code: str) -> pd.DataFrame:
    """按 年月 汇总指定门店的核心指标 + 各渠道分组金额。"""
    s = df[df["门店编码"].astype(str).str.strip() == str(store_code)].copy()
    rows = []
    for ym, g in s.groupby("年月"):
        row: dict[str, object] = {"年月": ym, "天数": len(g)}
        for key in ["系统销售金额", "工厂配送金额", "营业额", "门店收款小计", "门店应交", "门店实交"]:
            if key in g.columns:
                row[key] = round(sum(_to_float(v) for v in g[key]), 2)
        for group_name, src_cols in CHANNEL_GROUPS.items():
            total = 0.0
            for c in src_cols:
                if c in g.columns:
                    total += sum(_to_float(v) for v in g[c])
            row[group_name] = round(total, 2)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("年月").reset_index(drop=True)
