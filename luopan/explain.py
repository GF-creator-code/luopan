"""确定性依据卡生成器：解释每个市场为什么排在它现在的位置。

全部由规则从评分结果与原始数据生成，零 LLM、零新数字——与 guard.py 的台账
口径一致，是"更直观、解释为什么"的核心组件。上下文层（PPP、城镇化、关税、
CEPII 距离与 RCEP）只作佐证与风险提示，不影响评分本身。
"""
import statistics

from .config import CEPII

_DIM_CN = {
    "scale": "市场规模", "growth": "市场增速", "china_affinity": "渠道接受度",
    "purchase_power": "购买力", "digital": "数字渠道", "logistics": "物流",
}


def _rank_of(value, pool):
    """value 在 pool（可含 None）中的降序名次；value 为 None 返回 None。"""
    if value is None:
        return None
    solid = sorted([x for x in pool if x is not None], reverse=True)
    return solid.index(value) + 1 if value in solid else None


def _median(pool):
    solid = [x for x in pool if x is not None]
    return statistics.median(solid) if solid else None


def _scale_reason(raw, scales):
    v = raw["scale"]
    if v is None:
        return None
    pos = _rank_of(v, scales)
    med = _median(scales)
    note = "是该品类的主要消费市场" if pos == 1 else (
        "远高于候选市场中位数" if med and v > med * 2 else (
            "高于候选市场中位数" if med and v > med else "低于中位数，属利基市场"))
    return "进口规模 **{:.2f} 亿美元**（{} 年，候选市场第 {} 位，{}）".format(
        v / 1e8, raw["scale_year"], pos, note)


def _growth_reason(raw, growths):
    g = raw["growth"]
    if g is None:
        return "增速数据缺失（单年数据），按中位数回填计分"
    pos = _rank_of(g, growths)
    if g >= 0.15:
        judge = "需求快速扩张，进入窗口期"
    elif g >= 0.05:
        judge = "需求稳步增长"
    elif g >= 0:
        judge = "需求基本持平，存量竞争为主"
    else:
        judge = "需求在收缩，进入需谨慎"
    return "进口额年均增速 **{:.1%}**（第 {} 位）——{}".format(g, pos, judge)


def _share_reason(raw, shares):
    s = raw["china_share"]
    if s is None:
        return None
    pos = _rank_of(s, shares)
    if s >= 0.30:
        judge = "中国货已主导该市场，渠道成熟但竞争激烈，需差异化切入"
    elif s >= 0.15:
        judge = "渠道对中国货接受度高，且仍有提升空间"
    elif s >= 0.05:
        judge = "中国份额适中，竞争与机会并存"
    else:
        judge = "近乎空白市场：先发机会明显，但渠道开拓成本更高"
    return "中国份额 **{:.1%}**（第 {} 位）——{}".format(s, pos, judge)


def _pp_reason(raw, pps, price_tier):
    v = raw["purchase_power"]
    if v is None:
        return None
    tier_high = price_tier == "high"
    tier_low = price_tier == "low"
    fit = ("与高价位定位高度匹配，愿付溢价人群充足" if tier_high and v >= 30000 else
           "高价位定位需重点培育消费认知" if tier_high else
           "性价比定位与该市场购买力匹配" if tier_low and v < 15000 else
           "需以性价比切入该市场" if tier_low else
           "中端定位受众面广")
    return "人均 GDP **{:.0f} 美元**（第 {} 位）——{}".format(v, _rank_of(v, pps), fit)


def _context_reasons(r, ranked):
    """上下文佐证层：PPP 购买力交叉验证、城镇化、关税风险、地理与 RCEP。"""
    raw, iso3 = r["raw"], r["iso3"]
    out = []
    ppps = [x["raw"].get("gdp_ppp") for x in ranked]
    if raw.get("gdp_ppp") is not None:
        hi = _rank_of(raw["gdp_ppp"], ppps)
        out.append("购买力交叉验证：人均 GDP（PPP 口径）**{:.0f} 国际元**（第 {} 位）——"
                   "与美元现价口径相互印证".format(raw["gdp_ppp"], hi))
    urbans = [x["raw"].get("urban") for x in ranked]
    if raw.get("urban") is not None:
        lvl = "消费高度集中于城市，渠道铺设效率高" if raw["urban"] >= 80 else (
            "城镇化水平中等，城乡市场并存" if raw["urban"] >= 60 else
            "城镇化偏低，下沉市场与县域渠道空间大")
        out.append("城镇化率 **{:.0f}%**——{}".format(raw["urban"], lvl))
    tariffs = [x["raw"].get("tariff") for x in ranked]
    if raw.get("tariff") is not None:
        med = _median(tariffs)
        if med is not None and raw["tariff"] > med:
            out.append("⚠ 关税提示：制成品平均关税 **{:.1f}%**，高于候选市场中位数"
                       "（{:.1f}%），需按具体税则复核成本".format(raw["tariff"], med))
        else:
            out.append("制成品平均关税 **{:.1f}%**，不高于候选市场中位数，成本风险常规".format(
                raw["tariff"]))
    geo = CEPII.get(iso3)
    if geo:
        line = "距中国约 **{} 千公里**（CEPII）——{}".format(
            geo["distance_km"],
            "海运时效占优，适合小批量快反" if geo["distance_km"] <= 3500 else (
                "海运周期较长，需提前备货规划" if geo["distance_km"] >= 8000 else
                "海运半径适中"))
        if geo["rcep"]:
            line += "；**RCEP 成员**，享关税协定红利"
        out.append(line)
    return out


def evidence_for(ranked, price_tier="mid"):
    """为排名表逐市场生成依据卡。返回 [{rank, iso3, name, title, reasons, sub}]。"""
    scales = [r["raw"]["scale"] for r in ranked]
    growths = [r["raw"]["growth"] for r in ranked]
    shares = [r["raw"]["china_share"] for r in ranked]
    pps = [r["raw"]["purchase_power"] for r in ranked]

    cards = []
    for r in ranked:
        raw = r["raw"]
        reasons = [x for x in (
            _scale_reason(raw, scales),
            _growth_reason(raw, growths),
            _share_reason(raw, shares),
            _pp_reason(raw, pps, price_tier),
        ) if x]
        if raw["digital"] is not None:
            reasons.append("互联网渗透率 **{:.0f}%**——线上渠道基础{}".format(
                raw["digital"], "成熟" if raw["digital"] >= 75 else "一般"))
        if raw["logistics"] is not None:
            reasons.append("物流绩效 LPI **{:.1f}/5**——跨境履约{}".format(
                raw["logistics"], "顺畅" if raw["logistics"] >= 3.5 else "一般"))
        reasons.extend(_context_reasons(r, ranked))
        if r["imputed"]:
            reasons.append("⚠ 以下维度数据缺失按中位数回填：{}".format(
                "、".join(_DIM_CN[d] for d in r["imputed"])))

        top_dims = sorted(r["sub"].items(), key=lambda kv: -kv[1])[:2]
        title = "总分 **{:.2f}** ｜ 主要驱动：{}、{}".format(
            r["total"], _DIM_CN[top_dims[0][0]], _DIM_CN[top_dims[1][0]])
        cards.append({"rank": r["rank"], "iso3": r["iso3"], "name": r["name_zh"],
                      "title": title, "reasons": reasons, "sub": r["sub"]})
    return cards
