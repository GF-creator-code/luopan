# -*- coding: utf-8 -*-
"""出海罗盘 · Streamlit UI（本地体验与云端部署同一入口）。

选择式产品输入（品类/价位/区域偏好）→ Agent 评分 → 排名 + 六维雷达 +
逐市场确定性依据卡 + 台账核验的 LLM 点评。数据来源：世界银行 / UN Comtrade。
"""
import os

import pandas as pd
import streamlit as st

from luopan import cache as _cache
from luopan import comtrade, config
from luopan.agent import MarketAgent
from luopan.casefinder import find_cases_cached
from luopan.cases import alignment, cases_for
from luopan.charts import radar_small_multiples
from luopan.explain import evidence_for
from luopan.llm import LlmError
from luopan.profile import build_profile
from luopan.scoring import Weights

st.set_page_config(page_title="出海罗盘", page_icon="🧭", layout="wide",
                   initial_sidebar_state="expanded")

ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()
if ACCESS_CODE:
    entered = st.sidebar.text_input("访问码", type="password")
    if entered != ACCESS_CODE:
        st.sidebar.warning("请输入访问码（评审账号）后使用。")
        st.stop()

OTHER_LABEL = "🔍 其他品类（AI 自动识别 HS 编码）"
TIER_CODE = {"经济型": "low", "中端": "mid", "高端": "high"}
TIER_SUGGEST = {  # 价位段建议权重（%），滑条可再微调
    "经济型": {"scale": 30, "growth": 25, "china_affinity": 20,
               "purchase_power": 5, "digital": 10, "logistics": 10},
    "中端": {"scale": 25, "growth": 20, "china_affinity": 20,
             "purchase_power": 15, "digital": 10, "logistics": 10},
    "高端": {"scale": 20, "growth": 15, "china_affinity": 15,
             "purchase_power": 30, "digital": 10, "logistics": 10},
}

# ---------- 侧栏：权重工作台 ----------
with st.sidebar:
    st.markdown("## 🧭 出海罗盘")
    st.caption("AI Agent · 出海目标市场决策")
    st.divider()
    st.markdown("### 评分权重（%）")
    st.caption("六维可调，提交时自动归一化")
    _KEYS = {"scale": "规模", "growth": "增速", "china_affinity": "中国份额",
             "purchase_power": "购买力", "digital": "数字渠道", "logistics": "物流"}
    _DEFAULTS = TIER_SUGGEST["中端"]
    vals = {}
    for key, label in _KEYS.items():
        vals[key] = st.slider(label, 0, 40, _DEFAULTS[key], 5, key="w_" + key)
    _sum = sum(vals.values()) or 1
    weights = Weights(**{k: v / _sum for k, v in vals.items()})
    st.divider()
    st.caption("**数据来源**\n\n世界银行公开指标 · UN Comtrade")
    st.caption("**可信度**\n\n评分 100% 确定性代码可复算；LLM 叙事经数字台账守卫核验")

# ---------- 主区：选择式产品输入 ----------
st.title("🧭 出海罗盘")
st.markdown("三步选出你的出海目标市场：**选品类 → 调偏好 → 看依据**。")

st.markdown("### ① 描述你的产品（大类 → 细分品类）")
col_a, col_b = st.columns(2)
big = col_a.selectbox("大类", list(config.CATEGORY_TREE) + [OTHER_LABEL], key="big_cat")
if big == OTHER_LABEL:
    sub_item = None
    tier = col_b.selectbox("价位段", list(TIER_CODE), index=1)
    desc = st.text_area("请描述产品（AI 自动映射 6 位 HS 编码）",
                        key="input_text", height=72,
                        placeholder="例如：空气炸锅，家用大容量")
else:
    sub_names = [x["name"] for x in config.CATEGORY_TREE[big]]
    if st.session_state.get("sub_cat") not in sub_names:
        st.session_state.pop("sub_cat", None)  # 大类切换后旧细分失效，回默认
    sub_name = col_b.selectbox("细分品类", sub_names, key="sub_cat")
    sub_item = next(x for x in config.CATEGORY_TREE[big] if x["name"] == sub_name)
    tier = col_b.selectbox("价位段", list(TIER_CODE), index=1, key="tier_pick")
    desc = st.text_input("补充卖点或约束（可选，用于分析师点评）", key="input_text")

EX_SAMPLES = [("厨房与家居电器", "咖啡机（便携/户外）", "☕ 咖啡机"),
              ("厨房与家居电器", "扫地机器人/吸尘器", "🤖 扫地机器人"),
              ("智能宠物", "宠物智能用品（喂食器/饮水机）", "🐾 宠物智能")]


def _set_sample(big_name, sub_name):
    st.session_state["big_cat"] = big_name
    st.session_state["sub_cat"] = sub_name


ex_cols = st.columns(len(EX_SAMPLES))
for i, (bn, sn, label) in enumerate(EX_SAMPLES):
    ex_cols[i].button(label, key="ex{}".format(i), on_click=_set_sample,
                      args=(bn, sn), use_container_width=True)

region_sel = st.multiselect("② 区域偏好（可多选；不选 = 全球 21 个候选市场）",
                            list(config.REGIONS))


def _apply_tier(tier_name):
    for en, v in TIER_SUGGEST[tier_name].items():
        st.session_state["w_" + en] = v


st.button("⚖ 应用「{}」价位建议权重（侧栏滑条会自动更新）".format(tier),
          on_click=_apply_tier, args=(tier,))

go = st.button("🚀 开始分析", type="primary", use_container_width=True)


def fetch_missing(hs6, years, progress=None):
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
        except Exception as e:
            st.warning("抓取失败（reporter {} {}年）：{}".format(rep, y, e))
        if progress is not None and todo:
            progress.progress(min(1.0, i / len(todo)))


if go:
    if big == OTHER_LABEL:
        hs6 = None
        run_text = desc.strip()
        if not run_text:
            st.error("选择了「其他品类」，请先填写产品描述")
            st.stop()
    else:
        hs6 = sub_item["hs6"]
        run_text = "{}，{}定位".format(sub_item["name"], tier)
    try:
        prof = build_profile(run_text, hs6=hs6, price_tier=TIER_CODE[tier],
                             use_llm=True)
        if prof is None:
            st.error("无法确定产品品类（HS 编码），请把描述写得更具体些")
            st.stop()
        agent = MarketAgent()
        n, _years = agent.coverage(prof.hs6)
        if n < 21:
            st.info("该品类本地缓存覆盖 {}/21 个市场，正在按需实时抓取最新年份（约 1-2 分钟）…".format(n))
            fetch_missing(prof.hs6, (2023,), progress=st.progress(0.0))
        region_iso3s = None
        if region_sel:
            region_iso3s = {iso3 for rgn in region_sel for iso3 in config.REGIONS[rgn]}
        with st.status("🧭 Agent 运行中…", expanded=True) as status:
            result = MarketAgent().run(
                run_text, weights=weights, on_step=lambda s: st.markdown(
                    "**`[{}]`** {}".format(s["action"], s["observation"])),
                region_iso3s=region_iso3s)
            status.update(label="✅ 分析完成（{} 个市场已评分）".format(len(result.ranking or [])),
                          state="complete", expanded=False)
        st.session_state["result"] = result
        st.session_state["tier"] = tier
        st.session_state["evidence"] = evidence_for(result.ranking, TIER_CODE[tier]) \
            if result.ranking else []
        st.session_state["msgs"] = []
    except LlmError as e:
        st.error("LLM 调用失败：{}".format(e))

# ---------- 结果 ----------
result = st.session_state.get("result")
if result is None:
    st.info("← 选好产品后点「🚀 开始分析」")
    st.stop()
if result.error:
    st.error(result.error)
    st.stop()
if not result.ranking:
    st.error("所选区域内没有候选市场数据")
    st.stop()
if result.guard_warnings:
    st.warning("⚠️ 数字守卫警告（以下数字未在台账中，可能为模型推算）：{}".format(result.guard_warnings))

top = result.ranking[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("🥇 首选市场", top["name_zh"], "总分 {:.2f}".format(top["total"]))
m2.metric("首选市场进口规模", "{:.2f} 亿美元".format((top["raw"]["scale"] or 0) / 1e8),
          "{} 年进口".format(top["raw"]["scale_year"]))
m3.metric("首选市场中国份额",
          "{:.1%}".format(top["raw"]["china_share"]) if top["raw"]["china_share"] is not None else "待补")
m4.metric("已评分市场", "{} 个".format(len(result.ranking)))

tab_result, tab_trace, tab_method, tab_chat = st.tabs(
    ["📊 结果与依据", "🧭 Agent 轨迹", "📖 方法论", "💬 追问"])

with tab_result:
    rows = [{
        "排名": r["rank"], "市场": r["name_zh"], "总分": r["total"],
        "进口额(亿美元)": round((r["raw"]["scale"] or 0) / 1e8, 2),
        "中国份额": "{:.1%}".format(r["raw"]["china_share"]) if r["raw"]["china_share"] is not None else "待补",
        "年均增速": "{:.1%}".format(r["raw"]["growth"]) if r["raw"]["growth"] is not None else "待补",
        "待补维度": "、".join(r["imputed"]) or "-",
    } for r in result.ranking]
    df = pd.DataFrame(rows)
    c1, c2 = st.columns([5, 4])
    c1.dataframe(df, use_container_width=True, height=420, hide_index=True,
                 column_config={
                     "总分": st.column_config.NumberColumn(format="%.3f"),
                     "进口额(亿美元)": st.column_config.NumberColumn(format="%.2f"),
                 })
    c2.bar_chart(df.set_index("市场")["总分"].head(10), height=420,
                 use_container_width=True)

    st.markdown("### 六维画像（强项弱项一眼看清）")
    st.caption("每个雷达是该市场六项得分的 0-10 画像：越外扩越强。"
               "维度＝规模 / 增速 / 中国份额 / 购买力 / 数字渠道 / 物流。")
    st.pyplot(radar_small_multiples(result.ranking, 5))

    st.markdown("### 为什么是这些市场？（逐市场依据）")
    st.caption("依据由确定性规则直接从原始数据生成（零 LLM），每个数字都可溯源复算。")
    evidence = st.session_state.get("evidence") or evidence_for(result.ranking)
    for i, card in enumerate(evidence):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(card["rank"], "📍")
        with st.expander("{} 第{}名 {} — 总分 {:.2f}".format(
                medal, card["rank"], card["name"], result.ranking[i]["total"]),
                expanded=(i == 0)):
            st.markdown(card["title"])
            scols = st.columns(3)
            for j, (dk, v) in enumerate(card["sub"].items()):
                cn = {"scale": "规模", "growth": "增速", "china_affinity": "中国份额",
                      "purchase_power": "购买力", "digital": "数字渠道",
                      "logistics": "物流"}[dk]
                scols[j % 3].progress(min(1.0, v / 10),
                                      text="{} {:.1f}/10".format(cn, v))
            for reason in card["reasons"]:
                st.markdown("- " + reason)

    st.markdown("### 案例佐证（AI 发现相近品牌 + 可复制路径）")
    tier_now = st.session_state.get("tier", "中端")
    rank_of = {r["iso3"]: (r["rank"], r["name_zh"]) for r in result.ranking}
    with st.spinner("AI 案例研究员工作中（联网抓取素材 → 生成案例）…首次约 30 秒，同输入已缓存"):
        pack = find_cases_cached(result, tier_now)
    ai_cases, mode = pack["cases"], pack["mode"]
    snippets = pack.get("snippets", [])
    st.caption("案例来源：**{}**。事实请以品牌官方与公开报道为准（已要求可查证锚点）；"
               "市场对照由代码自动计算。".format(mode))
    if snippets:
        with st.expander("🌐 本次联网抓取的素材（{} 条）".format(len(snippets)), expanded=False):
            for s in snippets:
                st.markdown("- **{}**{}".format(
                    s["title"], (" — " + s["content"][:120]) if s["content"] else ""))
                if s["url"]:
                    st.caption("↳ " + s["url"])
    if ai_cases:
        for c in ai_cases:
            with st.container(border=True):
                head = "**{}**".format(c["brand"])
                if c["origin"]:
                    head += "（{}）".format(c["origin"])
                st.markdown(head + " · 共同性：{}".format(c["relation"] or "相近"))
                st.markdown("**它如何成功**：{}".format(c["how_succeeded"]))
                st.markdown("**你的复制路径**：{}".format(c["playbook"]))
                if c["iso3s"]:
                    hit, miss = alignment(c["iso3s"], result.ranking)
                    if hit:
                        names = "、".join(rank_of[m][1] for m in hit)
                        st.success("✅ 对照：其主攻市场中的 **{}**（{}）落在我们的 Top5".format(
                            len(hit), names))
                    if miss:
                        parts = "、".join("{}（第{}名）".format(rank_of[m][1], rk)
                                          for m, rk in miss if rk)
                        if parts:
                            st.info("ℹ 其余主攻市场：{}".format(parts))
                if c["markets"]:
                    st.caption("案例主攻市场：" + "、".join(c["markets"]))
                if c["anchors"]:
                    st.caption("可查证锚点：" + c["anchors"])
    else:
        st.info("AI 本次未给出案例（宁缺毋滥：没有确信可查证的相近品牌时不硬编）。"
                "联网抓取偶发失败会自动降级知识模式——换个描述再点一次开始分析即可。")

    with st.expander("内置精选案例（已人工核对，公开资料检索 2026-10）"):
        curated = cases_for(result.profile.hs6) if result.profile else []
        if not curated:
            st.caption("该品类无内置条目。")
        for case in curated:
            with st.container(border=True):
                st.markdown("**{}** · {}".format(case["brand"], case["relation"]))
                st.markdown(case["facts"])
                hit, miss = alignment(case["markets"], result.ranking)
                if hit:
                    names = "、".join(rank_of[m][1] for m in hit)
                    st.success("✅ 对照：其主攻市场中的 **{}**（{}）落在我们本次推荐的 Top5".format(
                        len(hit), names))
                if miss:
                    parts = "、".join("{}（第{}名）".format(rank_of[m][1], rk)
                                      for m, rk in miss if rk)
                    if parts:
                        st.info("ℹ 其余主攻市场：{}".format(parts))

    st.markdown("### 分析师点评")
    st.caption("LLM 生成；仅允许引用上表数字，且经数字台账守卫核验。")
    st.markdown(result.summary or "（LLM 叙事失败，但评分结果不受影响）")

with tab_trace:
    st.caption("五步执行轨迹全程可见——LLM 只做计划/品类映射/台账内叙事，"
               "评分与排名 100% 确定性代码，可复算。")
    for s in result.trace:
        with st.container(border=True):
            st.markdown("**第 {} 步 · `{}`**".format(s["step"], s["action"]))
            st.markdown(s["observation"])

with tab_method:
    st.markdown("### 这个排名是怎么算出来的")
    st.markdown("""
**六维加权评分**：每个候选市场在 6 个维度上先做归一化（0-10 分，本池内相对比较），
再按你左侧设置的权重加权求和。并列分按国家代码定序，**同一输入永远得到同一排名**。

**六个维度与数据源**

| 维度 | 数据 | 来源 |
|---|---|---|
| 市场规模（25%） | 该品类（HS6）自全球进口额，最新年 | UN Comtrade |
| 市场增速（20%） | 进口额首末年复合年均增速 | UN Comtrade |
| 渠道接受度（20%） | 该品类自中国进口 ÷ 自全球进口 | UN Comtrade |
| 购买力（15%） | 人均 GDP | 世界银行 WDI |
| 数字渠道（10%） | 互联网渗透率 | 世界银行 WDI |
| 物流（10%） | 物流绩效指数 LPI | 世界银行 WDI |

**为什么可信**：评分与报告由确定性代码生成，全部数字带年份与来源、可一键复算；
LLM 只负责计划、品类映射与叙事，其输出中的每个数字都要通过"数字台账守卫"
（不在台账中的数字会被显式标警）。缺失数据不做黑箱填补——按中位数回填并**显式标注**。
""")
    st.markdown("### 为什么用这些维度")
    st.markdown("""
- **规模 + 增速**回答"蛋糕多大、还在不在变大"——这是进入价值的天花板与时间窗；
- **渠道接受度（中国份额）**回答"当地渠道卖不卖中国货"——高＝基建成熟但竞争激烈，低＝蓝海但开拓成本高；
- **购买力**与价位段匹配（高端产品应上调其权重，经济型应下调——试试侧栏的"应用价位建议权重"）；
- **数字渠道 + 物流**回答"跨境卖货的履约基础行不行"。
""")

with tab_chat:
    st.caption("基于当前评分结果继续提问；回答中的数字同样经台账守卫核验。")
    if "msgs" not in st.session_state:
        st.session_state["msgs"] = []
    QUICK = ["如果只看东南亚还有哪些机会？", "第一名和第二名对比一下，选哪个？",
             "中国份额是什么意思？"]
    qcols = st.columns(3)

    def _ask(text_q):
        st.session_state["pending_q"] = text_q

    for i, qq in enumerate(QUICK):
        qcols[i].button(qq, key="q{}".format(i), on_click=_ask, args=(qq,),
                        use_container_width=True)
    for m in st.session_state["msgs"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q = st.session_state.pop("pending_q", None) or st.chat_input("输入追问…")
    if q:
        st.session_state["msgs"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        try:
            out = MarketAgent().followup(q, result)
            ans = out["answer"]
            if out.get("kind") == "rerank_region":
                chain = " > ".join("{}({})".format(r["name_zh"], r["total"])
                                   for r in out["ranking"])
                ans = "**{}子池排名**：{}\n\n{}".format(out["region"], chain, ans)
            if out.get("guard"):
                ans += "\n\n⚠️ 守卫警告：{}".format(out["guard"])
        except LlmError as e:
            ans = "LLM 调用失败：{}".format(e)
        st.session_state["msgs"].append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)
