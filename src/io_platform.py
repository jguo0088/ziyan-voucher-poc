# -*- coding: utf-8 -*-
"""第三方平台对账单解析（实收侧）。编码自动检测（UTF-8 BOM / GB18030 混用）。"""
from __future__ import annotations
import os, glob
import pandas as pd

# 外卖平台对账单目前仅 2025-10 一份数据
TAKEAWAY_MONTH = "2025-10"


def read_csv_auto(path: str) -> pd.DataFrame:
    """自动识别编码读 CSV，并去除微信/支付宝账单的反引号前缀。"""
    with open(path, "rb") as f:
        bom = f.read(3)
    enc = "utf-8-sig" if bom == b"\xef\xbb\xbf" else "gb18030"
    df = pd.read_csv(path, encoding=enc, dtype=str, on_bad_lines="skip", encoding_errors="replace")
    for c in df.columns:
        df[c] = df[c].astype(str).str.lstrip("`").str.strip()
    return df


def wechat_monthly(platform_dir: str, store_code: str, ym: str) -> dict | None:
    """微信门店 POS 流水：按月加总指定门店的实收与手续费。

    ym 形如 '2025-01'。文件名形如『…微信1286428601流水2025.01(1).csv』。
    """
    month = ym.replace("-", ".")  # 2025.01
    cands = glob.glob(os.path.join(platform_dir, f"*微信1286428601流水{month}*.csv"))
    if not cands:
        return None
    df = read_csv_auto(cands[0])
    if "设备号" not in df.columns:
        return None
    mine = df[df["设备号"].astype(str).str.contains(store_code, na=False)
              & (df["交易状态"] == "SUCCESS")]
    实收 = pd.to_numeric(mine.get("应结订单金额"), errors="coerce").fillna(0).sum()
    手续费 = pd.to_numeric(mine.get("手续费"), errors="coerce").fillna(0).sum()
    return {
        "渠道": "微信POS",
        "文件": os.path.basename(cands[0]),
        "笔数": int(len(mine)),
        "实收": round(float(实收), 2),
        "手续费": round(float(手续费), 2),
    }


def meituan_monthly(data_base: str, store_kw: str, ym: str) -> dict | None:
    """美团外卖：按门店关键词筛选，加总两个品牌账号的『商家应收款』（扣佣后实收）。"""
    if ym != TAKEAWAY_MONTH:
        return None
    mt_dir = os.path.join(data_base, "美团")
    if not os.path.isdir(mt_dir):
        return None
    实收, 笔数 = 0.0, 0
    for f in glob.glob(os.path.join(mt_dir, "*.xlsx")):
        try:
            df = pd.read_excel(f, sheet_name="订单明细", dtype=str)
        except Exception:
            continue
        if "门店名称" not in df.columns or "商家应收款" not in df.columns:
            continue
        mine = df[df["门店名称"].astype(str).str.contains(store_kw, na=False)]
        实收 += pd.to_numeric(mine["商家应收款"], errors="coerce").fillna(0).sum()
        笔数 += len(mine[df.get("交易类型", pd.Series(dtype=str)).astype(str).str.contains("外卖", na=False)]) if "交易类型" in mine.columns else len(mine)
    if 实收 == 0:
        return None
    return {"渠道": "美团外卖", "实收": round(float(实收), 2), "笔数": int(笔数)}


def eleme_monthly(data_base: str, store_kw: str, ym: str) -> dict | None:
    """饿了么外卖：按门店关键词筛选，加总『结算金额』。"""
    if ym != TAKEAWAY_MONTH:
        return None
    elm_dir = os.path.join(data_base, "饿了么")
    if not os.path.isdir(elm_dir):
        return None
    实收 = 0.0
    for f in glob.glob(os.path.join(elm_dir, "*.xlsx")):
        try:
            df = pd.read_excel(f, sheet_name="账单汇总", dtype=str)
        except Exception:
            continue
        if "门店名称" not in df.columns or "结算金额" not in df.columns:
            continue
        mine = df[df["门店名称"].astype(str).str.contains(store_kw, na=False)]
        实收 += pd.to_numeric(mine["结算金额"], errors="coerce").fillna(0).sum()
    if 实收 == 0:
        return None
    return {"渠道": "饿了么外卖", "实收": round(float(实收), 2), "笔数": 0}
