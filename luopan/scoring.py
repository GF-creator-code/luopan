"""市场特征构建、归一化与加权评分。

全部确定性纯代码（stdlib）：同输入必同输出，报告引用的每个数字都能从
fixtures + 本模块重算，直接回应章程"可验证"要求。
"""
import statistics
from dataclasses import dataclass

from .config import COUNTRIES

# 评分用 WB 指标；关税不入评分，只在报告风险层提示
WB_KEYS = {
    "purchase_power": "NY.GDP.PCAP.CD",
    "digital": "IT.NET.USER.ZS",
    "logistics": "LP.LPI.OVRL.XQ",
}


@dataclass
class Weights:
    scale: float = 0.25           # 市场规模：该 HS6 自全球进口额（最新年）
    growth: float = 0.20          # 市场增长：进口额首末年 CAGR
    china_affinity: float = 0.20  # 供给接受度：自中国进口 / 自全球进口
    purchase_power: float = 0.15  # 购买力：人均 GDP
    digital: float = 0.10         # 数字就绪：互联网渗透率
    logistics: float = 0.10       # 物流就绪：LPI

    def __post_init__(self):
        vals = [self.scale, self.growth, self.china_affinity,
                self.purchase_power, self.digital, self.logistics]
        for v in vals:
            if v < 0:
                raise ValueError("权重不能为负: {}".format(vals))
        total = sum(vals)
        if abs(total - 1.0) > 1e-9:
            raise ValueError("权重和必须为 1.0，当前 {}".format(total))


def _latest(points):
    """[(year, value)] → 最新非空 (year, value)。"""
    pts = [(y, v) for y, v in points if v is not None]
    if not pts:
        return None, None
    return max(pts, key=lambda p: p[0])


def build_features(hs6: str, wb_records, cty_records):
    """按市场池逐国构建原始特征。不填补不改写，缺失一律 None，由评分层填补并标记。"""
    feats = {}
    for iso3, info in COUNTRIES.items():
        if iso3 == "CHN":
            continue  # 中国是供给端参照，不是评分目标
        rows = [r for r in cty_records
                if r.get("hs6") == hs6 and r.get("reporter") == info["cty"]]
        world = {r["year"]: r["value_usd"] for r in rows if r.get("partner") == 0}
        china = {r["year"]: r["value_usd"] for r in rows if r.get("partner") == 156}

        scale_year, scale = _latest(world.items())
        china_share = None
        if scale:  # scale 为 0 或 None 都无法算份额
            cn = china.get(scale_year)
            if cn is not None:
                china_share = cn / scale

        growth = None
        yrs = sorted(y for y, v in world.items() if v)
        if len(yrs) >= 2 and yrs[-1] > yrs[0]:
            v0, v1 = world[yrs[0]], world[yrs[-1]]
            if v0 > 0 and v1 > 0:
                growth = (v1 / v0) ** (1.0 / (yrs[-1] - yrs[0])) - 1.0

        f = {"iso3": iso3, "name_zh": info["name_zh"],
             "scale": scale, "scale_year": scale_year,
             "china_share": china_share, "growth": growth}
        for key, ind in WB_KEYS.items():
            y, v = _latest([(r["year"], r["value"]) for r in wb_records
                            if r.get("indicator") == ind and r.get("iso3") == iso3])
            f[key] = v
            f[key + "_year"] = y
        feats[iso3] = f
    return feats


def _minmax10(values):
    """{key: value|None} → ({key: 0-10}, imputed_keys)。缺失用中位数回填并标记。"""
    have = {k: v for k, v in values.items() if v is not None}
    if not have:
        return {k: 5.0 for k in values}, set(values)
    lo, hi = min(have.values()), max(have.values())
    med = statistics.median(have.values())

    def to10(v):
        if hi == lo:
            return 5.0
        return (v - lo) / (hi - lo) * 10.0

    out, imputed = {}, set()
    for k, v in values.items():
        if v is None:
            out[k] = to10(med)
            imputed.add(k)
        else:
            out[k] = to10(v)
    return out, imputed


def score_markets(features, weights=None):
    """返回按总分降序的列表（并列分按 iso3 排序，保证复现）。"""
    w = weights or Weights()
    dims = {
        "scale": {i: f["scale"] for i, f in features.items()},
        "growth": {i: f["growth"] for i, f in features.items()},
        "china_affinity": {i: f["china_share"] for i, f in features.items()},
        "purchase_power": {i: f["purchase_power"] for i, f in features.items()},
        "digital": {i: f["digital"] for i, f in features.items()},
        "logistics": {i: f["logistics"] for i, f in features.items()},
    }
    subs, imputed = {}, {}
    for name, values in dims.items():
        subs[name], imputed[name] = _minmax10(values)

    results = []
    for iso3, f in features.items():
        total = sum(getattr(w, name) * subs[name][iso3] for name in dims)
        results.append({
            "iso3": iso3,
            "name_zh": f["name_zh"],
            "rank": 0,
            "total": round(total, 4),
            "sub": {name: round(subs[name][iso3], 3) for name in dims},
            "raw": {k: f[k] for k in ("scale", "scale_year", "china_share", "growth",
                                      "purchase_power", "digital", "logistics")},
            "imputed": sorted(n for n in dims if iso3 in imputed[n]),
        })
    results.sort(key=lambda r: (-r["total"], r["iso3"]))
    for i, r in enumerate(results, 1):
        r["rank"] = i
    return results
