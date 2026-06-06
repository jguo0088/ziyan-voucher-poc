# -*- coding: utf-8 -*-
"""规则学习（现场可展示）：从历史序时账识别门店收入的科目组合、摘要模式、借贷方向。

定位为「辅助生成规则草案 + 财务确认」，不是凭空学全套规则。
"""
from __future__ import annotations
import pandas as pd

LOC_FIELDS = ["外部凭证抬头文本", "项目文本", "客户名称", "成本中心描述"]


def _locate_store_vouchers(jdf: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """定位含门店关键词的凭证全部行项目。"""
    def hit(r):
        return any(keyword in str(r.get(c, "")) for c in LOC_FIELDS)
    vnos = jdf[jdf.apply(hit, axis=1)]["外部凭证号"].unique()
    return jdf[jdf["外部凭证号"].isin(vnos)].copy()


def learn_from_journal(jdf: pd.DataFrame, keyword: str = "虬长") -> dict:
    """返回：科目组合频次、摘要模式、收入凭证的借贷方向草案。"""
    sub = _locate_store_vouchers(jdf, keyword)

    # 1) 科目使用频次（科目 × 借贷方向）
    sub["_dc"] = sub["借贷标识"].map(lambda x: "借" if str(x) == "S" else "贷")
    combo = (sub.groupby(["科目号", "科目名称", "_dc"]).size()
             .reset_index(name="次数").sort_values("次数", ascending=False))

    # 2) 高频摘要模式
    zhaiyao = sub["外部凭证抬头文本"].dropna().astype(str)
    patterns = zhaiyao.value_counts().head(10).reset_index()
    patterns.columns = ["摘要", "次数"]

    # 3) 收入凭证的借贷方向草案（含主营业务收入的凭证）
    inc_vnos = sub[sub["科目名称"].astype(str).str.contains("主营业务收入", na=False)]["外部凭证号"].unique()
    inc_lines = sub[sub["外部凭证号"].isin(inc_vnos)]
    rule_draft = (inc_lines.groupby(["科目名称", "_dc"]).size()
                  .reset_index(name="出现次数").sort_values("出现次数", ascending=False))

    return {
        "凭证数": int(sub["外部凭证号"].nunique()),
        "科目组合": combo,
        "摘要模式": patterns,
        "收入规则草案": rule_draft,
    }
