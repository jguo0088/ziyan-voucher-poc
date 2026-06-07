# -*- coding: utf-8 -*-
"""POC 路径与门店配置。数据指向客户原始目录，不拷贝大文件。"""
import os

# 客户原始数据根目录（虬长店资料）
DATA_BASE = r"D:\JASON\BDO\01. Projects\紫燕\门店资料-上海虬长店"

# 关键输入文件
F_SETTLEMENT = os.path.join(DATA_BASE, "5.01紫燕直营店结算报表.xlsx")
F_JOURNAL = os.path.join(DATA_BASE, "紫燕食品-序时账.xlsx")
F_STORE_FLOW = os.path.join(DATA_BASE, "4.20门店销售流水查询-上海虬长店.xlsx")
F_PAY_SUMMARY = os.path.join(DATA_BASE, "4.13门店历史销售支付汇总-上海虬长店.xlsx")

# 第三方平台流水目录（微信门店POS流水等）
PLATFORM_DIR = os.path.join(DATA_BASE, "紫燕股份-第三方平台流水")

# POC 目标门店
STORE_CODE = "80010129"
STORE_NAME = "上海虬长店"

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# DeepSeek（优先环境变量，否则从 skill-store 的 apps/web/.env 读）
def _read_env_file(key: str) -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web", ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _get_secret(key: str, default: str = "") -> str:
    """读取密钥：① 环境变量 ② Streamlit Cloud Secrets（云端）③ 本地 apps/web/.env。"""
    v = os.environ.get(key)
    if v:
        return v
    try:
        import streamlit as st  # 云端部署：从 Streamlit Secrets 读
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return _read_env_file(key) or default


DEEPSEEK_API_KEY = _get_secret("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _get_secret("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-chat"

# 通义千问 Qwen（OpenAI 兼容接口）
QWEN_API_KEY = _get_secret("QWEN_API_KEY")
QWEN_BASE_URL = _get_secret("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = "qwen-plus"

# 本地是否存在真实数据（云端通常 False → 自动切到上传模式）
HAS_LOCAL_DATA = os.path.exists(F_SETTLEMENT)
