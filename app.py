# -*- coding: utf-8 -*-
"""出海罗盘 · Streamlit UI（本地体验与云端部署同一入口）。

数据来源：世界银行公开指标 + UN Comtrade 公开预览接口；LLM 走环境变量/.env。
部署时在托管平台 Secrets 配置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，
可另配 ACCESS_CODE 作为访问码门（兼作评审账号，保护 API 额度）。
"""
import os

import pandas as pd
import streamlit as st

from luopan import cache as _cache
from luopan import comtrade, config
from luopan.agent import MarketAgent
from luopan.llm import LlmError
from luopan.profile import build_profile
from luopan.scoring import Weights

st.set_page_config(page_title="出海罗盘", page_icon="🧭", layout="wide")

ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()
if ACCESS_CODE:
    entered = st.sidebar.text_input("访问码", type="password")
    if entered != ACCESS_CODE:
        st.warning("请输入访问码（评审账号）后使用。")
        st.stop()

st.title("🧭 出海罗盘")
st.caption("输入你的产品，Agent 自动采集公开贸易数据、六维加权评分排序，"
           "产出带数据溯源的出海目标市场决策。数据来源：世界银行 / UN Comtrade。")

EXAMPLES = [
    "便携咖啡机，零售价300元，主攻线上渠道",
    "扫地机器人，中高端定位",
    "宠物智能喂食器，预算有限先打1-2个国家",
]

with st.sidebar:
    st.header("评分权重（%）")
    st.caption("六维可调，提交时自动归一化")
    _KEYS = {"规模": "scale", "增速": "growth", "中国份额": "china_affinity",
             "购买力": "purchase_power", "数字渠道": "digital", "物流": "logistics"}
    _DEFAULTS = {"规模": 25, "增速": 20, "中国份额": 20, "购买力": 15, "数字渠道": 10, "物流": 10}
    vals = {label: st.slider(label, 0, 40, dft, 5) for label, dft in _DEFAULTS.items()}
    _sum = sum(vals.values()) or 1
    st.caption("归一化后权重：" + "、".join(
        "{} {}".format(k, round(v / _sum * 100)) for k, v in vals.items()))
    weights = Weights(**{_KEYS[k]: v / _sum for k, v in vals.items()})


def _set_example(i):
    st.session_state["input_text"] = EXAMPLES[i]


text = st.text_area("产品描述", key="input_text", height=72)
ex_cols = st.columns(len(EXAMPLES))
for i in range(len(EXAMPLES)):
    ex_cols[i].button("示例 {}".format(i + 1), key="ex{}".format(i),
                      on_click=_set_example, args=(i,), use_container_width=True)


def fetch_missing(hs6, years, progress=None):
    """按需实时抓取缺失的 Comtrade 数据（写本地缓存，评分前由 agent 合并）。"""
    todo = []
    for iso3, info in config.COUNTRIES.items():
        if iso3 == "CHN":
            continue
        for y in years:
            if _cache.get("comtrade", comtrade.cache_key(info["cty"], hs6, y)) is None:
                todo.append((info["cty"], y))
    for i, (rep, y) in enumerate(todo, 1):
        try:
            comtrade.fetch_year(rep, hs6, y)
        except Exception as e:  # 限流/网络失败时跳过该国，评分层会标记待补
            st.warning("抓取失败（reporter {} {}年）：{}".format(rep, y, e))
        if progress is not None and todo:
            progress.progress(min(1.0, i / len(todo)))
    return len(todo)


if st.button("开始分析", type="primary", use_container_width=True):
    if not text.strip():
        st.error("请先填写产品描述")
        st.stop()
    try:
        prof = build_profile(text, use_llm=True)
        if prof is None:
            st.error("无法确定产品品类（HS 编码）。请把描述写得更具体些。")
            st.stop()
        agent = MarketAgent()
        n, _years = agent.coverage(prof.hs6)
        if n < 21:
            st.info("该品类本地缓存覆盖 {}/21 个市场，正在按需实时抓取最新年份（约 1 分钟）…".format(n))
            fetch_missing(prof.hs6, (2023,), progress=st.progress(0.0))
            agent = MarketAgent()  # 重载合并后的数据
        with st.spinner("Agent 运行中：计划 → 品类定位 → 覆盖检查 → 六维评分 → 叙事…"):
            result = agent.run(text, weights=weights)
        st.session_state["result"] = result
        st.session_state["msgs"] = []
    except LlmError as e:
        st.error("LLM 调用失败：{}".format(e))

result = st.session_state.get("result")
if result is None:
    st.info("← 填好产品描述后点「开始分析」")
    st.stop()

if result.error:
    st.error(result.error)
    st.stop()

if result.guard_warnings:
    st.warning("数字守卫警告（以下数字未在台账中，可能为模型推算）：{}".format(result.guard_warnings))

st.subheader("市场排名")
rows = [{
    "排名": r["rank"], "市场": r["name_zh"], "总分": r["total"],
    "进口额(亿美元)": round((r["raw"]["scale"] or 0) / 1e8, 2),
    "中国份额": "{:.1%}".format(r["raw"]["china_share"]) if r["raw"]["china_share"] is not None else "待补",
    "年均增速": "{:.1%}".format(r["raw"]["growth"]) if r["raw"]["growth"] is not None else "待补",
    "待补维度": "、".join(r["imputed"]) or "-",
} for r in result.ranking]
c1, c2 = st.columns([3, 2])
c1.dataframe(pd.DataFrame(rows), use_container_width=True, height=520, hide_index=True)
c2.bar_chart(pd.DataFrame(rows).set_index("市场")["总分"].head(10), height=520)

st.subheader("Agent 执行轨迹")
with st.expander("展开五步轨迹（可验证智能体交互）", expanded=True):
    for s in result.trace:
        st.markdown("**[{}] `{}`** {}".format(s["step"], s["action"], s["observation"]))

st.subheader("分析师点评")
st.write(result.summary or "（LLM 叙事失败，但评分结果不受影响）")

st.subheader("追问")
if "msgs" not in st.session_state:
    st.session_state["msgs"] = []
for m in st.session_state["msgs"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
q = st.chat_input("例如：只看东南亚还有哪些机会？/ 第一名和第二名对比一下 / 中国份额是什么意思")
if q:
    st.session_state["msgs"].append({"role": "user", "content": q})
    try:
        out = MarketAgent().followup(q, result)
        ans = out["answer"]
        if out.get("kind") == "rerank_region":
            chain = " > ".join("{}({})".format(r["name_zh"], r["total"]) for r in out["ranking"])
            ans = "**{}子池排名**：{}\n\n{}".format(out["region"], chain, ans)
        if out.get("guard"):
            ans += "\n\n⚠️ 守卫警告：{}".format(out["guard"])
    except LlmError as e:
        ans = "LLM 调用失败：{}".format(e)
    st.session_state["msgs"].append({"role": "assistant", "content": ans})
    st.rerun()
