"""产品档案 schema 与 HS6 映射：关键词校对表（确定性、离线）为主，LLM 可选兜底。"""
import json
import os
import re
from dataclasses import dataclass

from . import envload
from .config import CATEGORY_TREE, HS_PRESETS

HS6_RE = re.compile(r"^\d{6}$")


@dataclass
class ProductProfile:
    raw_text: str
    hs6: str
    hs_name_zh: str = ""
    price_tier: str = "mid"      # low / mid / high
    matched_by: str = "manual"   # keyword / llm / manual


# (关键词组, hs6)：命中关键词个数多者胜，同分取先出现者（专有词排前面）
HS_TABLE = [
    (("便携咖啡机", "手压咖啡", "espresso", "咖啡机"), "841981"),
    (("扫地机器人", "吸尘器", "robot vacuum", "vacuum"), "850811"),
    (("投影仪", "投影机", "projector"), "852862"),
    (("宠物喂食器", "宠物饮水机", "智能宠物", "pet feeder"), "850980"),
    (("电咖啡壶", "滴滤咖啡机"), "851671"),
    (("玩具", "toy"), "950300"),
    (("笔记本电脑", "笔记本", "laptop", "平板电脑"), "847130"),
    (("智能手表", "手环", "smartwatch", "smart watch"), "851762"),
    (("胶片冲洗", "冲洗设备", "冲洗机", "暗房", "显影"), "901010"),
    (("翻拍", "片夹", "拷贝台", "负片支架", "观片器"), "901090"),
]


def lookup_hs6(text):
    """校对表匹配，返回 hs6 或 None。"""
    t = (text or "").lower()
    best, best_hits = None, 0
    for kws, hs6 in HS_TABLE:
        hits = sum(1 for k in kws if k.lower() in t)
        if hits > best_hits:
            best, best_hits = hs6, hits
    return best


def _code_from_text(content):
    """从 LLM 输出提取编码：优先 6 位；只有 4 位章标题时补 00。"""
    m = re.search(r"\d{6}", content)
    if m:
        return m.group(0)
    m = re.search(r"\d{4}", content)
    return m.group(0) + "00" if m else None


_MAP_SYSTEM = ("你是海关商品归类专家。对产品描述执行三步："
               "①拆分：把描述拆成独立的功能部件；"
               "②映射：为每个部件映射 6 位 HS 细分编码，并确定作为整体归类的 primary 核心编码；"
               "③归位：从给定的两级品类目录中选出最匹配的大类（选不出就留空）。"
               "铁律：编码只用你确信存在的海关编码，拿不准宁可留空。全部简体中文。")


def _extract_json_object(text):
    if not text:
        return None
    m = re.search(r"\{", text)
    if not m:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(text[m.start():])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def llm_map_product(text, llm=None):
    """AI 拆分匹配：描述 → 部件拆解 + 逐部件 HS 映射 + 目录归位。
    返回 {"components":[{"name","hs6","why"}], "primary_hs6", "major", "rationale"} 或 None。"""
    if llm is None:
        from .llm import LlmClient
        try:
            llm = LlmClient()
        except Exception:
            return None
    tree_text = "\n".join("【{}】{}".format(major, "、".join(
        "{}({})".format(x["name"], x["hs6"]) for x in subs))
        for major, subs in CATEGORY_TREE.items())
    prompt = (
        "两级品类目录（可用于归位）：\n{tree}\n\n"
        "产品描述：{desc}\n\n"
        "请输出 JSON（不要任何其他文字）：\n"
        '{{"components":[{{"name":"部件名","hs6":"6位编码","why":"归类理由(≤30字)"}}],'
        '"primary_hs6":"作为整体归类的核心编码",'
        '"major":"最匹配的大类名（从目录选，无贴切的可留空）",'
        '"rationale":"整体归类思路(≤60字)"}}'.format(tree=tree_text, desc=(text or ""))
    )
    data = _extract_json_object(llm.chat(
        [{"role": "system", "content": _MAP_SYSTEM},
         {"role": "user", "content": prompt}], max_tokens=1200))
    if not data:
        return None
    components = []
    for c in (data.get("components") or []):
        if not isinstance(c, dict):
            continue
        hs6 = _code_from_text(str(c.get("hs6", "")))
        if hs6 and c.get("name"):
            components.append({"name": str(c["name"]).strip(), "hs6": hs6,
                               "why": (c.get("why") or "").strip()})
    primary = _code_from_text(str(data.get("primary_hs6", ""))) \
        or (components[0]["hs6"] if components else None)
    major = (data.get("major") or "").strip()
    if major not in CATEGORY_TREE:
        major = None
    if not primary:
        return None
    return {"components": components, "primary_hs6": primary,
            "major": major, "rationale": (data.get("rationale") or "").strip()}


def llm_lookup_hs6(text):
    """旧接口兼容：只返回主编码（推荐使用 llm_map_product / smart_build_profile）。"""
    mapping = llm_map_product(text)
    return mapping["primary_hs6"] if mapping else None


def smart_build_profile(text, price_tier="mid", llm=None):
    """三级识别：关键词 → AI 拆分匹配 → None。
    返回 (ProductProfile|None, info)；info 含 matched_by/components/major/rationale。"""
    info = {"matched_by": None, "components": [], "major": None, "rationale": ""}
    prof = build_profile(text, price_tier=price_tier)  # 第一级：关键词（零 LLM）
    if prof:
        info["matched_by"] = "keyword"
        return prof, info
    mapping = llm_map_product(text, llm=llm)  # 第二级：AI 拆分匹配
    if not mapping:
        return None, info
    info["matched_by"] = "llm_split"
    info["components"] = mapping["components"]
    info["major"] = mapping["major"]
    info["rationale"] = mapping["rationale"]
    prof = build_profile(text, hs6=mapping["primary_hs6"], price_tier=price_tier)
    if prof:
        prof.matched_by = "llm_split"
        for major, subs in CATEGORY_TREE.items():
            for x in subs:
                if x["hs6"] == prof.hs6:
                    prof.hs_name_zh = x["name"]
        return prof, info
    return None, info


def build_profile(text, hs6=None, price_tier="mid", use_llm=False):
    """构建产品档案；hs6 显式给出时优先（UI 手选路径）。映射失败返回 None。"""
    matched_by = "manual"
    if hs6:
        hs6 = str(hs6)
    else:
        hs6 = lookup_hs6(text)
        matched_by = "keyword"
        if hs6 is None and use_llm:
            hs6 = llm_lookup_hs6(text)
            matched_by = "llm"
    if hs6 is None or not HS6_RE.match(hs6):
        return None
    if price_tier not in ("low", "mid", "high"):
        raise ValueError("price_tier 必须是 low/mid/high")
    return ProductProfile(
        raw_text=text or "",
        hs6=hs6,
        hs_name_zh=HS_PRESETS.get(hs6, {}).get("name_zh", ""),
        price_tier=price_tier,
        matched_by=matched_by,
    )
