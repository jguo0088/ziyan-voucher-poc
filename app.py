# -*- coding: utf-8 -*-
"""紫燕门店收入智能制单 POC —— Streamlit 演示界面（麦肯锡风）。

运行：streamlit run app.py
"""
import os, sys, io, warnings
from datetime import datetime
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import streamlit as st

import config
from src.io_settlement import load_settlement, monthly_summary
from src.voucher import gen_revenue_voucher, gen_discount_voucher, gen_takeaway_voucher, check_balance
from src.validate import validate_voucher
from src.rule_learning import learn_from_journal
from src.io_platform import wechat_monthly, meituan_monthly, eleme_monthly
from src.reconcile import classify_channels, reconcile_wechat, reconcile_takeaway
from src.llm import analyze_anomalies, chat_with_context, summarize_rules
from src import report

st.set_page_config(page_title="紫燕智能制单 POC", layout="wide", initial_sidebar_state="expanded")

# ============================ 视觉系统（McKinsey 风） ============================
st.markdown("""
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{
  --navy:#0B1F33; --navy2:#13304d; --blue:#2251FF; --ink:#0B1F33;
  --muted:#5B6B7B; --line:#E4E9F0; --panel:#F5F7FB; --bg:#FFFFFF;
  --ok:#1A7F5A; --warn:#B7791F; --danger:#C0392B;
}
html, body, [class*="css"]{ font-family:'Inter','Segoe UI','Microsoft YaHei',sans-serif; }
.stApp{ background:var(--bg); }
footer{ display:none !important; }
[data-testid="stDecoration"]{ display:none !important; }
.block-container{ padding-top:1.2rem; padding-bottom:3rem; max-width:1180px; }

/* 顶部品牌 banner */
.mck-banner{
  background:linear-gradient(110deg,var(--navy) 0%,var(--navy2) 100%);
  border-radius:14px; padding:26px 32px; margin-bottom:18px;
  display:flex; justify-content:space-between; align-items:center;
  box-shadow:0 6px 24px rgba(11,31,51,.18);
}
.mck-banner h1{ color:#fff; font-size:25px; font-weight:700; margin:0; letter-spacing:.3px; }
.mck-banner p{ color:#A9C0D6; font-size:13px; margin:6px 0 0; }
.mck-brand{ text-align:right; color:#8FB0CC; font-size:12px; line-height:1.6; }
.mck-brand b{ color:#fff; font-size:15px; letter-spacing:2px; }
.mck-accent{ display:inline-block; width:34px; height:3px; background:var(--blue); border-radius:2px; margin-bottom:8px; }

/* 步骤进度条 */
.mck-steps{ display:flex; gap:0; margin:6px 0 18px; padding:16px 10px 10px;
  background:linear-gradient(135deg,#F7F9FC 0%,#EAF1FB 100%); border:1px solid var(--line); border-radius:12px; }
.mck-step{ flex:1; text-align:center; position:relative; padding-top:24px; font-size:12px; color:var(--muted); font-weight:500; letter-spacing:.2px; }
.mck-step:before{ content:''; position:absolute; top:10px; left:0; right:0; height:2px;
  background:linear-gradient(90deg,#2251FF,#9DBBEA); opacity:.45; }
.mck-step .dot{ position:absolute; top:2px; left:50%; transform:translateX(-50%);
  width:18px; height:18px; border-radius:50%; background:#fff; border:2px solid #C7D3E3; }
.mck-step.active{ color:var(--navy); font-weight:600; }
.mck-step.active .dot{ border-color:var(--blue);
  background:radial-gradient(circle at 35% 30%,#5A9CE6,#2251FF);
  box-shadow:0 0 0 4px rgba(34,81,255,.15),0 2px 6px rgba(34,81,255,.35); }
.mck-step:first-child:before{ left:50%; } .mck-step:last-child:before{ right:50%; }

/* section 标题 */
.mck-sec{ display:flex; align-items:center; gap:12px; margin:26px 0 6px; }
.mck-sec .num{ background:var(--navy); color:#fff; font-weight:700; font-size:13px;
  width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.mck-sec .t{ font-size:18px; font-weight:700; color:var(--ink); }
.mck-sec .d{ font-size:12.5px; color:var(--muted); margin-left:auto; }

/* 卡片 */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#fff; border:1px solid var(--line)!important; border-radius:12px;
  box-shadow:0 1px 3px rgba(11,31,51,.04);
}
/* metric */
div[data-testid="stMetric"]{ background:var(--panel); border:1px solid var(--line);
  border-radius:10px; padding:14px 16px; }
div[data-testid="stMetricValue"]{ font-size:22px; font-weight:700; color:var(--navy);
  font-variant-numeric:tabular-nums; }
div[data-testid="stMetricLabel"]{ color:var(--muted); font-size:12px; }
/* 按钮 */
.stButton>button{ border-radius:8px; border:1px solid var(--blue); color:var(--blue);
  font-weight:600; background:#fff; }
.stButton>button:hover{ background:var(--blue); color:#fff; }
.stDownloadButton>button{ border-radius:8px; background:var(--navy); color:#fff; border:none; font-weight:600; }
.stDownloadButton>button:hover{ background:var(--blue); }
/* dataframe 圆角 */
div[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:10px; }
/* 侧栏 */
section[data-testid="stSidebar"]{ background:var(--panel); border-right:1px solid var(--line); }
/* AI 对话：紧凑字体、收紧行距 */
[data-testid="stChatMessage"]{ padding:4px 0; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li{
  font-size:13px !important; line-height:1.5 !important; margin-bottom:3px !important; }
[data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3{
  font-size:13.5px !important; font-weight:600 !important; margin:6px 0 3px !important; }
[data-testid="stChatMessage"] ol, [data-testid="stChatMessage"] ul{ margin:2px 0 4px !important; padding-left:18px; }
/* Tab：按钮组风格，背景差异化提示可点击 */
div[data-baseweb="tab-list"]{ gap:6px; background:var(--panel); padding:6px;
  border-radius:10px; border:1px solid var(--line); margin-bottom:10px; flex-wrap:wrap; }
button[data-baseweb="tab"]{ background:#fff !important; border:1px solid var(--line) !important;
  border-radius:8px !important; padding:5px 16px !important; color:var(--muted); font-weight:500; }
button[data-baseweb="tab"]:hover{ border-color:var(--blue) !important; color:var(--blue); background:#F0F5FF !important; }
button[data-baseweb="tab"][aria-selected="true"]{ background:var(--navy) !important;
  border-color:var(--navy) !important; box-shadow:0 2px 6px rgba(11,31,51,.2); }
button[data-baseweb="tab"][aria-selected="true"] *{ color:#fff !important; }
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"]{ display:none !important; }
/* 嵌套子 tab（制单内）：轻量下划线风，与主 tab 区分层级 */
[data-baseweb="tab-panel"] div[data-baseweb="tab-list"]{ background:transparent; border:none; padding:0 0 2px; margin-bottom:6px; }
[data-baseweb="tab-panel"] button[data-baseweb="tab"]{ background:transparent !important; border:none !important;
  border-bottom:2px solid transparent !important; border-radius:0 !important; padding:4px 12px !important; box-shadow:none !important; }
[data-baseweb="tab-panel"] button[data-baseweb="tab"]:hover{ background:transparent !important; color:var(--blue); }
[data-baseweb="tab-panel"] button[data-baseweb="tab"][aria-selected="true"]{ background:transparent !important;
  border-bottom:2px solid var(--blue) !important; box-shadow:none !important; }
[data-baseweb="tab-panel"] button[data-baseweb="tab"][aria-selected="true"] *{ color:var(--blue) !important; }
</style>
""", unsafe_allow_html=True)


def banner():
    st.markdown("""
    <div class="mck-banner">
      <div>
        <div class="mck-accent"></div>
        <h1><i class="fa-solid fa-file-invoice-dollar" style="margin-right:10px;opacity:.85"></i>紫燕门店收入 · 智能制单 POC</h1>
        <p>用实际原始数据，验证「线上审单 + 自动制凭证」可行性 · 上海虬长店</p>
      </div>
      <div class="mck-brand"><b>BDO · 立信</b><br>数智创新部<br>Financial AI Lab</div>
    </div>
    """, unsafe_allow_html=True)


def stepper(active: int):
    names = ["01 上传", "02 归集", "03 对账", "04 规则", "05 制单", "06 AI归因", "07 输出", "08 问答"]
    html = '<div class="mck-steps">'
    for i, n in enumerate(names, 1):
        cls = "mck-step active" if i <= active else "mck-step"
        html += f'<div class="{cls}"><span class="dot"></span>{n}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def sec(num: str, title: str, desc: str = ""):
    st.markdown(f'<div class="mck-sec"><span class="num">{num}</span>'
                f'<span class="t">{title}</span><span class="d">{desc}</span></div>',
                unsafe_allow_html=True)


@st.cache_data(show_spinner="读取结算报表…")
def _settlement():
    return load_settlement(config.F_SETTLEMENT)


@st.cache_data(show_spinner="读取序时账（22MB，首次稍候）…")
def _journal():
    if not os.path.exists(config.F_JOURNAL):
        return pd.DataFrame()  # 云端无序时账 → 空表，相关功能优雅降级
    return pd.read_excel(config.F_JOURNAL, dtype=str)


def get_journal():
    """优先用上传的序时账（session），否则读本地（云端无则空表）。"""
    jdf = st.session_state.get("journal_df")
    if jdf is not None:
        return jdf
    return _journal()


# ============================ 页面 ============================
banner()

# 侧边栏静态部分（始终显示，不被上传拦截影响）
with st.sidebar:
    st.markdown('### <i class="fa-solid fa-sliders" style="color:#2251FF"></i> 制单参数', unsafe_allow_html=True)
    st.caption("上传当月结算报表后，下方出现门店与会计月份选择。")
    st.divider()
    _model = st.radio("AI 模型", ["DeepSeek-V4-Flash", "DeepSeek-V4-Pro", "通义千问 Qwen3.7-Plus"],
                      help="切换大模型，影响规则归纳 / 异常归因 / 对话")
    st.divider()
    st.markdown("##### 控制原则")
    for _p in ["金额 100% 来自原始 Excel", "AI 不生成金额 / 不造科目",
               "借贷平衡由程序校验", "异常 / 大额强制人工复核", "全流程留痕可追溯"]:
        st.markdown(f"<span style='font-size:12.5px;color:#5B6B7B'>· {_p}</span>", unsafe_allow_html=True)

# 按所选模型确定 LLM 调用参数（影响 04 规则归纳 / 06 异常归因 / 08 对话）
if "Qwen" in _model:
    LLM_KEY, LLM_BASE, LLM_MODEL = config.QWEN_API_KEY, config.QWEN_BASE_URL, config.QWEN_MODEL
elif "Pro" in _model:
    LLM_KEY, LLM_BASE, LLM_MODEL = config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL, config.DEEPSEEK_PRO_MODEL
else:
    LLM_KEY, LLM_BASE, LLM_MODEL = config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL, config.DEEPSEEK_MODEL

# ---------- 01 数据上传与批次登记 ----------
sec("01", "数据上传与批次登记", "财务上传当月原始数据，系统生成批次号确保可追溯")
store_code = config.STORE_CODE
store_name = config.STORE_NAME
with st.container(border=True):
    _modes = (["使用内置样例（上海虬长店）", "上传新数据"]
              if config.HAS_LOCAL_DATA else ["上传新数据"])
    mode = st.radio("数据来源", _modes, horizontal=True, label_visibility="collapsed")
    uploaded_settlement = None
    uploaded_journal = None
    files = []
    if mode == "上传新数据":
        up = st.file_uploader("上传结算报表 / 序时账 / 平台对账单（可多选）",
                              accept_multiple_files=True, type=["xlsx", "csv", "zip"])
        if up:
            files = [f.name for f in up]
            # 按文件名分类：含"序时"→序时账；含"结算"→结算报表
            for f in up:
                if "序时" in f.name:
                    uploaded_journal = f
                elif "结算" in f.name:
                    uploaded_settlement = f
            # 兜底：未识别到结算报表，则取第一个非序时账的 xlsx
            if uploaded_settlement is None:
                for f in up:
                    if f.name.lower().endswith(".xlsx") and "序时" not in f.name:
                        uploaded_settlement = f
                        break
            # 上传的序时账读入 session（供规则学习 / 对照），按文件名去重避免重复读
            if uploaded_journal is not None and st.session_state.get("journal_name") != uploaded_journal.name:
                with st.spinner("读取上传的序时账…"):
                    st.session_state.journal_df = pd.read_excel(uploaded_journal, dtype=str)
                    st.session_state.journal_name = uploaded_journal.name
        st.caption("已识别『结算报表』用于归集制单；上传『序时账』后可用于规则学习 / 凭证对照。")
    if "batch_id" not in st.session_state:
        st.session_state.batch_id = "ZY" + datetime.now().strftime("%Y%m%d%H%M%S")
    src_files = files or ["5.01紫燕直营店结算报表.xlsx", "紫燕食品-序时账.xlsx"]
    st.dataframe(pd.DataFrame([{
        "批次号": st.session_state.batch_id, "上传人": "财务-演示账号",
        "上传时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "数据文件": "； ".join(src_files), "规则版本": "R-REV v1", "处理状态": "已登记",
    }]), use_container_width=True, hide_index=True)

    if uploaded_settlement is not None:
        df = load_settlement(uploaded_settlement)
        stores = sorted(df["门店编码"].astype(str).str.strip().unique())
        store_code = st.selectbox("选择门店（来自上传文件）", stores)
        nm = df[df["门店编码"].astype(str).str.strip() == store_code]["门店名称"]
        store_name = nm.iloc[0] if len(nm) else store_code
        st.success(f"已解析上传结算报表：识别到 {len(stores)} 个门店、{df['年月'].nunique()} 个月份，制单将基于上传数据。")
    elif config.HAS_LOCAL_DATA:
        df = _settlement()
    else:
        st.info("请在上方上传结算报表 Excel 以开始制单（线上版需手动上传数据）。")
        st.stop()

summary = monthly_summary(df, store_code)
months = summary["年月"].tolist()

with st.sidebar:
    st.metric("目标门店", store_name)
    ym = st.selectbox("会计月份", months, index=0)

row = summary[summary["年月"] == ym].iloc[0].to_dict()

tab_g, tab_r, tab_l, tab_v, tab_a, tab_o, tab_c = st.tabs(
    ["清洗归集", "渠道对账", "规则学习", "自动制单", "AI异常归因", "对照与输出", "AI助手"])

# ---------- 02 清洗与月度归集 ----------
with tab_g:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("系统销售金额", f"{row['系统销售金额']:,.0f}")
    c2.metric("营业额", f"{row['营业额']:,.0f}")
    c3.metric("门店收款小计", f"{row['门店收款小计']:,.0f}")
    c4.metric("当月天数", f"{int(row['天数'])}")
    with st.expander("查看 12 个月全渠道归集明细"):
        st.dataframe(summary.set_index("年月").T, use_container_width=True)

# ---------- 03 渠道初判与应收实收对账 ----------
with tab_r:
    st.markdown("**渠道初判 —— 拟入科目 / 处理方式 / 置信度**")
    st.dataframe(classify_channels(row), use_container_width=True, hide_index=True)
    st.markdown("**应收 ↔ 实收对账（多源交叉核对）**")
    store_kw = store_name.replace("上海", "").replace("店", "").strip() or "虬长"
    recs = []
    wx = wechat_monthly(config.PLATFORM_DIR, store_code, ym)
    rec = reconcile_wechat(float(row.get("POS-微信(应收)", 0)), wx)
    if rec:
        recs.append(rec)
    mt_rec = reconcile_takeaway("美团外卖", float(row.get("外卖-美团", 0)),
                                meituan_monthly(config.DATA_BASE, store_kw, ym))
    if mt_rec:
        recs.append(mt_rec)
    elm_rec = reconcile_takeaway("饿了么外卖", float(row.get("外卖-饿了么", 0)),
                                 eleme_monthly(config.DATA_BASE, store_kw, ym))
    if elm_rec:
        recs.append(elm_rec)
    if recs:
        st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
        st.caption("微信差异≈退款/跨月，手续费计财务费用；外卖差异≈平台抽佣/服务费。"
                   "（外卖对账单目前仅 2025-10；支付宝 POS 待接入）")
    else:
        st.info("未找到该月平台流水文件，对账跳过。")

# ---------- 04 规则学习 ----------
with tab_l:
    if st.button("从历史序时账学习记账规则"):
        jdf_learn = get_journal()
        if jdf_learn.empty:
            st.warning("当前环境无历史序时账数据（线上演示需随结算报表一起上传序时账）。规则学习暂不可用。")
        else:
            learned = learn_from_journal(jdf_learn, keyword="虬长")
            st.session_state.learned = learned
            stats_text = (
                f"门店历史凭证数：{learned['凭证数']}\n"
                f"【科目使用频次（科目 / 借贷 / 次数）】\n{learned['科目组合'].head(15).to_string(index=False)}\n"
                f"【高频摘要】\n{learned['摘要模式'].to_string(index=False)}\n"
                f"【收入凭证借贷方向】\n{learned['收入规则草案'].to_string(index=False)}"
            )
            with st.spinner("DeepSeek 归纳记账逻辑中…"):
                try:
                    st.session_state.rule_summary = summarize_rules(
                        stats_text, LLM_KEY, LLM_BASE, LLM_MODEL)
                except Exception as e:
                    st.session_state.rule_summary = f"（归纳失败：{e}）"
    if st.session_state.get("learned"):
        learned = st.session_state.learned
        st.success(f"已分析虬长店历史凭证 {learned['凭证数']} 个：")
        lc1, lc2 = st.columns(2)
        lc1.markdown("**收入凭证 · 借贷方向（Python 统计）**")
        lc1.dataframe(learned["收入规则草案"], use_container_width=True, hide_index=True)
        lc2.markdown("**高频摘要模式（Python 统计）**")
        lc2.dataframe(learned["摘要模式"], use_container_width=True, hide_index=True)
        if st.session_state.get("rule_summary"):
            st.markdown("**DeepSeek 归纳的记账逻辑（语义理解，供财务确认）**")
            st.info(st.session_state.rule_summary)
    else:
        st.info("点击按钮：Python 统计科目组合/摘要，DeepSeek 再语义归纳出记账逻辑。")

# ---------- 05 自动制单 ----------
lines = gen_revenue_voucher(ym, row)
disc_lines = gen_discount_voucher(ym, row)
takeaway_lines = gen_takeaway_voucher(ym, row)
all_lines = lines + disc_lines + takeaway_lines


def _draft_view(ls):
    return pd.DataFrame([{
        "借贷": l["借贷"], "科目编码": l["科目编码"], "科目名称": l["科目名称"],
        "金额": l["金额"], "rule_id": l["rule_id"], "来源字段": l["source_field"],
    } for l in ls])


def _show_balance(ls):
    b, c, ok = check_balance(ls)
    (st.success if ok else st.error)(
        f"借合计 {b:,.2f} ｜ 贷合计 {c:,.2f} ｜ 借贷平衡：{'通过' if ok else '不平'}")


with tab_v:
    t1, t2, t3, t4 = st.tabs(["① 收入确认凭证", "② 折扣调整（草案）", "③ 外卖应收结转（暂估）", "④ 程序校验清单"])
    with t1:
        st.dataframe(_draft_view(lines), use_container_width=True, hide_index=True)
        _show_balance(lines)
    with t2:
        if disc_lines:
            st.dataframe(_draft_view(disc_lines), use_container_width=True, hide_index=True)
            _show_balance(disc_lines)
            st.caption("折扣口径 = 券/储值/优惠各渠道合计（近似），与真实凭证差约 0.1%，待财务确认精确口径。")
        else:
            st.info("当月无折扣调整。")
    with t3:
        if takeaway_lines:
            st.dataframe(_draft_view(takeaway_lines), use_container_width=True, hide_index=True)
            _show_balance(takeaway_lines)
            st.caption("外卖应收按结算报表暂估结转至『应收账款-外卖平台』；拿到平台账单后，差异（抽佣）计平台服务费。")
        else:
            st.info("当月无外卖收入。")
    with t4:
        st.dataframe(validate_voucher(all_lines), use_container_width=True, hide_index=True)
        st.caption("校验涵盖收入 / 折扣 / 外卖全部分录；未通过项转人工复核清单。")

# ---------- 06 AI 异常归因 ----------
with tab_a:
    成本候选 = float(row.get("工厂配送金额", 0) or 0)
    储值额 = float(row.get("储值/会员", 0) or 0)
    anomalies = [{
        "异常项": "成本结转金额存疑",
        "描述": f"系统暂用『工厂配送金额』{成本候选:,.2f} 作为成本，但工厂配送含未售库存，"
                f"真实已售成本应更低，结算报表无成本数据。",
        "涉及科目": "主营业务成本-直营店 / 发出商品",
    }]
    try:
        if rec and abs(rec.get("差异", 0)) > 0:
            anomalies.append({
                "异常项": "微信应收↔实收差异",
                "描述": f"结算报表应收 {rec['结算报表应收']:,.2f}，微信平台实收 {rec['平台实收']:,.2f}，"
                        f"差异 {rec['差异']:,.2f}（{rec['差异率%']}%），手续费 {rec.get('手续费/抽佣', 0):,.2f}。",
                "涉及科目": "应收账款-直营店 / 财务费用-手续费",
            })
    except NameError:
        pass
    if 储值额 > 0:
        anomalies.append({
            "异常项": "储值卡消费缺明细",
            "描述": f"储值/会员渠道金额 {储值额:,.2f}，缺储值卡消费核销明细，无法精确确认收入与集团结算。",
            "涉及科目": "预收账款-储值卡",
        })

    st.markdown(f"**系统识别出 {len(anomalies)} 个异常 / 待确认项**")
    st.dataframe(pd.DataFrame(anomalies), use_container_width=True, hide_index=True)
    if st.button("调用 DeepSeek 分析异常项"):
        with st.spinner("AI 分析中…"):
            parsed, _raw = analyze_anomalies(anomalies, LLM_KEY, LLM_BASE, LLM_MODEL)
        st.session_state.llm_result = parsed
    if st.session_state.get("llm_result"):
        st.success("AI 归因完成（仅判断与建议，金额 / 科目由程序确定）：")
        st.dataframe(pd.DataFrame(st.session_state.llm_result), use_container_width=True, hide_index=True)

# ---------- 07 对照 + 输出 ----------
with tab_o:
    jdf = get_journal()
    vno = None
    if not jdf.empty:
        period = str(int(ym.split("-")[1]))
        target_rev = round(float(row["门店收款小计"]) / (1 + 0.13), 2)
        for v in jdf[(jdf["会计期间"] == period) & (jdf["科目号"] == "60010100")]["外部凭证号"].unique():
            rev = jdf[(jdf["外部凭证号"] == v) & (jdf["科目号"] == "60010100")]["本币金额"].astype(float).sum()
            if abs(rev - target_rev) < 1.0:
                vno = v
                break
    if vno:
        one = jdf[jdf["外部凭证号"] == vno]
        true_map = {}
        for _, r in one.iterrows():
            dc = "借" if str(r["借贷标识"]) == "S" else "贷"
            true_map[(r["科目号"], dc)] = true_map.get((r["科目号"], dc), 0) + float(r["本币金额"])
        gen_map = {}
        for l in lines:
            gen_map[(l["科目编码"], l["借贷"])] = gen_map.get((l["科目编码"], l["借贷"]), 0) + l["金额"]
        rows = []
        for k in sorted(set(gen_map) | set(true_map)):
            g, t = gen_map.get(k, 0), true_map.get(k, 0)
            diff = round(g - t, 2)
            rows.append({"借贷": k[1], "科目编码": k[0], "AI生成": round(g, 2),
                         "真实凭证": round(t, 2), "差异": diff, "判定": "一致" if abs(diff) < 1 else "待查"})
        st.markdown(f"**与真实凭证 `{vno}` 逐科目对照**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("收入侧精确匹配；成本侧因结算报表无成本数据存在差异（待接存货系统）。")

    st.divider()
    batch = st.session_state.batch_id
    need_review = abs(row["工厂配送金额"]) > 0
    draft_df = report.build_voucher_draft(batch, ym, all_lines, need_review, "成本数据待接存货系统，请财务核对成本金额")
    review_df = report.build_manual_review(batch, [{
        "事项": f"{ym} 直营店成本结转", "异常原因": "结算报表无成本数据，工厂配送金额≠已售成本",
        "需补充资料": "存货/成本核算系统的当月已售成本", "复核意见": "", "最终确认": "",
    }] if need_review else [])
    audit_logs = [{
        "调用场景": "收入确认制单（规则确定性生成）", "输入摘要": f"{ym}门店收款小计={row['门店收款小计']}",
        "AI输出": "借应收账款-直营店/贷主营收入+销项税", "模型版本": "rule-only", "提示词版本": "-",
        "规则版本": "R-REV-DIRECT v1", "调用时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }]
    if st.session_state.get("llm_result"):
        audit_logs.append({
            "调用场景": "异常归因（步骤6-7）", "输入摘要": f"{len(st.session_state.llm_result)} 个异常项",
            "AI输出": "性质判断+归因+复核建议（无金额、无科目）", "模型版本": LLM_MODEL,
            "提示词版本": "anomaly-v1", "规则版本": "-",
            "调用时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    audit_df = report.build_audit_log(batch, audit_logs)

    def _xlsx(d):
        buf = io.BytesIO(); d.to_excel(buf, index=False); return buf.getvalue()

    d1, d2, d3 = st.columns(3)
    d1.download_button("下载voucher_draft.xlsx", _xlsx(draft_df), f"{batch}_voucher_draft.xlsx", use_container_width=True)
    d2.download_button("下载manual_review.xlsx", _xlsx(review_df), f"{batch}_manual_review.xlsx", use_container_width=True)
    d3.download_button("下载ai_audit_log.xlsx", _xlsx(audit_df), f"{batch}_ai_audit_log.xlsx", use_container_width=True)
    st.caption(f"批次号：{batch}")

    st.divider()
    st.markdown("**人工复核 —— 财务编辑后保存，沉淀为规则优化样本**")
    if review_df.empty:
        st.success("本月无强制复核项，分录草稿可直接进入导入流程。")
    else:
        edited = st.data_editor(review_df, use_container_width=True, hide_index=True, key="review_editor")
        if st.button("保存复核结果（沉淀为优化样本）"):
            st.session_state.review_saved = edited.to_dict("records")
        if st.session_state.get("review_saved"):
            st.success(f"已沉淀 {len(st.session_state.review_saved)} 条复核样本 —— "
                       f"将用于优化关键词 / 阈值 / 科目映射 / AI 提示词（步骤 10 闭环）。")

    st.markdown("**财务系统导入模板**")
    imp_df = report.build_import_template(batch, ym, all_lines)
    st.dataframe(imp_df, use_container_width=True, hide_index=True)
    st.download_button("下载voucher_import.xlsx（财务系统导入格式）", _xlsx(imp_df),
                       f"{batch}_voucher_import.xlsx", use_container_width=True)
    st.caption("POC 阶段优先 Excel 导入；后续可对接金蝶 / 用友 / SAP 的 RPA 或 API。")

# ---------- 08 对话式财务助手 ----------
with tab_c:
    _ctx = [f"门店：{store_name}，会计月份：{ym}",
            f"系统销售={row['系统销售金额']:.0f}，营业额={row['营业额']:.0f}，门店收款小计={row['门店收款小计']:.0f}"]
    _ctx.append("各渠道金额：" + "，".join(
        f"{k}={float(row.get(k, 0) or 0):.0f}" for k in
        ["POS-微信(应收)", "POS-支付宝(应收)", "外卖-美团", "外卖-饿了么", "现金", "储值/会员", "团购券类", "折扣调整"]))
    if recs:
        _ctx.append("应收实收对账：" + "；".join(
            f"{r['渠道']} 应收{r['结算报表应收']:.0f}/实收{r['平台实收']:.0f}/差异{r['差异']:.0f}({r['差异率%']}%)"
            for r in recs))
    _ctx.append("已生成凭证：" + "；".join(f"{l['借贷']} {l['科目名称']} {l['金额']:.2f}" for l in all_lines))
    try:
        if anomalies:
            _ctx.append("待确认/异常项：" + "；".join(a["异常项"] for a in anomalies))
    except NameError:
        pass
    context_text = "\n".join(_ctx)

    st.caption("试试问：")
    examples = ["这个月外卖差异为什么这么大？", "这套凭证做审计要重点看哪里？", "外卖应收暂估为什么这么记？"]
    ecols = st.columns(len(examples))
    for i, q in enumerate(examples):
        if ecols[i].button(q, key=f"chat_ex_{i}", use_container_width=True):
            st.session_state.pending_q = q

    for m in st.session_state.get("chat_history", []):
        _av = ":material/smart_toy:" if m["role"] == "assistant" else ":material/person:"
        st.chat_message(m["role"], avatar=_av).markdown(m["content"])

    user_q = st.chat_input("问我关于本月制单的任何问题…")
    if not user_q and st.session_state.get("pending_q"):
        user_q = st.session_state.pop("pending_q")
    if user_q:
        st.session_state.setdefault("chat_history", []).append({"role": "user", "content": user_q})
        with st.spinner("AI 思考中…"):
            try:
                ans = chat_with_context(user_q, context_text, st.session_state.chat_history[:-1],
                                        LLM_KEY, LLM_BASE, LLM_MODEL)
            except Exception as e:
                ans = f"（调用失败：{e}）"
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()
