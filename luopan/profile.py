"""产品档案 schema 与 HS6 映射：关键词校对表（确定性、离线）为主，LLM 可选兜底。"""
import os
import re
from dataclasses import dataclass

from . import envload
from .config import HS_PRESETS

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


def llm_lookup_hs6(text):
    """校对表未命中时的可选兜底：OpenAI-compatible LLM 映射 6 位 HS 码。
    需 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 环境变量；未配置或任何异常返回 None。"""
    base = os.environ.get("LLM_BASE_URL")
    key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL")
    if not (base and key and model):
        envload.load_dotenv()
        base = base or os.environ.get("LLM_BASE_URL")
        key = key or os.environ.get("LLM_API_KEY")
        model = model or os.environ.get("LLM_MODEL")
    if not (base and key and model):
        return None
    try:
        import requests

        resp = requests.post(
            base.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={
                "model": model,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": ("把产品映射到中国海关 6 位 HS 细分编码，只输出 6 位数字，"
                                "不要解释。组合套件/多部件产品按其核心功能部件归类；"
                                "摄影暗房/翻拍/冲洗器材在第 90 或 37 章。\n产品描述：" + (text or "")),
                }],
            },
            timeout=30,
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return _code_from_text(content)
    except Exception:
        return None


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
