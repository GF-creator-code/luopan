"""AI 案例研究员：为任意品类发现相近品牌案例并给出复制路径。

三模式（自动选择）：
- 联网抓取（默认）：CrawlSearch 直接抓 Bing 中国版/百度结果页，真实素材喂给 LLM
- 联网 API：配置 SEARCH_API_KEY 后用 Tavily
- 知识模式：DISABLE_CRAWL=1 且无 key 时，LLM 基于训练知识（强防编造约束）

结果按 (品类, 价位, 描述) 落盘缓存。市场对照由确定性代码计算。
"""
import hashlib
import json
import re

from . import cache as _cache
from .config import NAME_TO_ISO3
from .llm import LlmClient
from .websearch import get_search_client

_SYSTEM = ("你是出海案例研究员。铁律：只使用你高度确信真实存在、且被公开报道过的"
           "公司与事实，宁可少而准，不可编造；对该品类没有把握时返回空数组 []。"
           "全部用简体中文，品牌名可保留英文。联网检索线索仅作参考，"
           "与你确信的事实冲突时以确信的为准。")


def _mode_of(client):
    if client is None:
        return "知识模式（未联网）"
    return "Tavily API" if type(client).__name__ == "TavilySearch" else "网页抓取（Bing/百度）"


def _cache_key(profile, price_tier):
    raw = "{}|{}|{}".format(profile.hs6, price_tier, profile.raw_text)
    return "aiv2_" + hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def _market_name_to_iso3(name):
    name = (name or "").strip()
    if name in NAME_TO_ISO3:
        return NAME_TO_ISO3[name]
    up = name.upper()
    if len(up) == 3 and up in NAME_TO_ISO3.values():
        return up
    return None


def _extract_json_array(text):
    if not text:
        return []
    m = re.search(r"\[", text)
    if not m:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(text[m.start():])
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _normalize(cases):
    out = []
    for c in cases:
        if not isinstance(c, dict):
            continue
        brand = (c.get("brand") or "").strip()
        how = (c.get("how_succeeded") or "").strip()
        playbook = (c.get("playbook") or "").strip()
        if not brand or not how or not playbook:
            continue
        m_names, iso3s = [], []
        for name in (c.get("markets") or []):
            code = _market_name_to_iso3(name)
            if code and code not in iso3s:
                iso3s.append(code)
                m_names.append(name.strip())
            elif name.strip():
                m_names.append(name.strip())  # 不在候选池的市场照常展示
        out.append({
            "brand": brand,
            "origin": (c.get("origin") or "").strip(),
            "relation": (c.get("relation") or c.get("similarity") or "").strip(),
            "how_succeeded": how,
            "playbook": playbook,
            "anchors": (c.get("anchors") or "").strip(),
            "markets": m_names,
            "iso3s": iso3s,
        })
        if len(out) >= 3:
            break
    return out


def _collect_snippets(search_client, category):
    if search_client is None:
        return []
    rows = []
    for q in ("{} 出海 品牌 成功 案例".format(category),
              "{} Chinese brand overseas success".format(category)):
        try:
            for item in search_client.search(q, max_results=4):
                rows.append({"query": q, "title": item.get("title", ""),
                             "content": item.get("content", ""),
                             "url": item.get("url", "")})
        except Exception:
            continue  # 单条查询失败不影响另一条
    return rows[:8]


def _snippets_block(snippets):
    if not snippets:
        return ""
    lines = ["- {}：{}".format(s["title"], s["content"]) for s in snippets]
    return "\n\n联网检索线索（仅作参考，与你确信的事实冲突时以确信的为准）：\n" + "\n".join(lines)


def research_cases(profile, ranked, llm, price_tier="mid", search_client=None):
    """生成案例并返回 (cases, meta)。meta 含 snippets（联网素材）与 mode（引擎模式）。"""
    top5 = "、".join("{}（{}分）".format(r["name_zh"], r["total"]) for r in ranked[:5])
    pool = "、".join(r["name_zh"] for r in ranked)
    category = profile.raw_text.strip() or profile.hs_name_zh or profile.hs6
    snippets = _collect_snippets(search_client, category)
    prompt = (
        "产品品类：{cat}（HS {hs6}），价位段：{tier}。\n"
        "我们为其计算的候选市场评分 Top5：{top5}。\n"
        "候选市场全集（markets 字段只能从这里选）：{pool}\n\n"
        "请找出 **2 个**真实出海品牌案例，要求：\n"
        "1. 与该品类相同或相近——可以是同类产品、相近需求/技术、相近人群或相似渠道"
        "打法；品牌可以来自任何国家，产品不必完全相同，但必须说清共同性与可复制性\n"
        "2. markets 字段从候选市场全集的中文名里选（该品牌实际主攻的市场）\n"
        "3. how_succeeded：该品牌如何取得成功（≤120字）\n"
        "4. playbook：结合候选市场排名与价位段，说明用户的品牌如何复制该路径取得市场（≤120字）\n"
        "5. anchors：可查证锚点（公司全称/总部/代表产品线）\n\n"
        "只输出 JSON 数组，不要任何其他文字。格式："
        '[{{"brand":"","origin":"","relation":"","markets":[""],"how_succeeded":"",'
        '"playbook":"","anchors":""}}]'.format(
            cat=category, hs6=profile.hs6, tier=price_tier, top5=top5, pool=pool)
    ) + _snippets_block(snippets)

    text = llm.chat([{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}], max_tokens=6000, timeout=180)
    return _normalize(_extract_json_array(text)), {"snippets": snippets,
                                                   "mode": _mode_of(search_client)}


def find_cases(profile, ranked, llm, price_tier="mid", search_client=None):
    """兼容入口：只返回案例列表。"""
    return research_cases(profile, ranked, llm,
                          price_tier=price_tier, search_client=search_client)[0]


def find_cases_cached(result, price_tier="mid", use_search=True):
    """带磁盘缓存的入口；返回 {"cases","snippets","mode"}，失败不抛异常。"""
    empty = {"cases": [], "snippets": [], "mode": "失败（已重试）"}
    if result is None or result.profile is None or not result.ranking:
        return empty
    key = _cache_key(result.profile, price_tier)
    hit = _cache.get("aicases", key)
    if hit is not None and isinstance(hit.get("data"), dict):
        return hit["data"]
    search_client = get_search_client() if use_search else None
    try:
        llm = LlmClient()
        cases, meta = research_cases(result.profile, result.ranking, llm,
                                     price_tier=price_tier, search_client=search_client)
    except Exception:
        try:  # LLM/网络偶发抖动，重试一次（WB 同款先例）
            cases, meta = research_cases(result.profile, result.ranking, llm,
                                         price_tier=price_tier, search_client=search_client)
        except Exception:
            return empty
    data = {"cases": cases, "snippets": meta["snippets"], "mode": meta["mode"]}
    if cases:
        _cache.put("aicases", key,
                   {"hs6": result.profile.hs6, "tier": price_tier}, data)
    return data
