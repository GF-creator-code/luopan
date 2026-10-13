"""AI 案例研究员单测：解析/归一化/降级，全部 FakeLlm 零网络。"""
import json

from luopan.casefinder import _extract_json_array, _normalize, find_cases
from luopan.profile import build_profile

GOOD = json.dumps([{
    "brand": "Wacaco",
    "origin": "香港便携咖啡机品牌",
    "relation": "同品类",
    "markets": ["美国", "德国", "日本"],
    "how_succeeded": "专注便携浓缩，产品极简耐用，深耕户外人群",
    "playbook": "先攻美国、德国线上渠道，以户外与差旅场景切入",
    "anchors": "Wacaco Company Limited，总部香港，Nanopresso 系列",
}], ensure_ascii=False)

RANKED = [{"name_zh": "美国", "total": 7.0},
          {"name_zh": "德国", "total": 4.4},
          {"name_zh": "日本", "total": 4.0}]


class FakeLlm:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def chat(self, messages, temperature=0.0, max_tokens=2000, timeout=None):
        self.calls.append(messages[-1]["content"])
        return self.reply


def _profile():
    return build_profile("便携咖啡机", price_tier="mid")


def test_extract_json_array_with_surrounding_prose():
    text = '好的，结果如下：\n' + GOOD + '\n以上供参考。'
    data = _extract_json_array(text)
    assert len(data) == 1 and data[0]["brand"] == "Wacaco"


def test_find_cases_parses_maps_markets_to_iso3():
    cases = find_cases(_profile(), RANKED, FakeLlm(GOOD))
    assert len(cases) == 1
    assert cases[0]["iso3s"] == ["USA", "DEU", "JPN"]
    assert "便携浓缩" in cases[0]["how_succeeded"]
    assert "复制路径" not in cases[0]["playbook"]  # 字段原样保留


def test_find_cases_garbage_returns_empty():
    assert find_cases(_profile(), RANKED, FakeLlm("该品类我没有把握，没有可查证案例。")) == []


def test_normalize_drops_incomplete_entries():
    assert _normalize([{"brand": "只有名字"}, "垃圾", {"brand": "B", "how_succeeded": "x", "playbook": "y"}]) != []
    assert len(_normalize([{"brand": "只有名字"}, "垃圾"])) == 0


def test_normalize_accepts_similarity_key():
    cases = _normalize([{"brand": "Ninja", "similarity": "同为厨房小家电",
                         "markets": ["美国"], "how_succeeded": "差异化",
                         "playbook": "亚马逊切入", "anchors": "SharkNinja"}])
    assert cases[0]["relation"] == "同为厨房小家电"
