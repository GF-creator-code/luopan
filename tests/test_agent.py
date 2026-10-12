"""Agent 单测：FakeLlm 注入（测试零网络），覆盖管线结构、守卫、四类追问分支。"""
import json
from pathlib import Path

import pytest

from luopan.agent import MarketAgent
from luopan.guard import build_ledger, check as guard_check, extract_numbers
from luopan.llm import LlmError
from luopan.llm import LlmClient
from luopan.scoring import Weights

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"


class FakeLlm:
    """按调用顺序返回脚本化回复；超出脚本时重复最后一条。"""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, temperature=0.0, max_tokens=2000):
        self.calls.append(messages[-1]["content"][:60])
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["records"]


@pytest.fixture(scope="module")
def data():
    return _load("worldbank.json"), _load("comtrade.json")


@pytest.fixture(scope="module")
def result(data):
    wb, cty = data
    llm = FakeLlm(["解析产品并评分", "美国规模最大，进口14.15亿美元，中国份额23.6%，推荐首选美国。"])
    return MarketAgent(llm=llm, wb_records=wb, cty_records=cty).run("便携咖啡机，零售价300元")


def test_llm_unconfigured_raises_clean(monkeypatch):
    import luopan.llm as llm_mod
    monkeypatch.setattr(llm_mod.envload, "load_dotenv", lambda *a, **k: None)
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(LlmError):
        LlmClient()


def test_pipeline_structure_and_determinism(result):
    assert result.error is None
    assert result.profile.hs6 == "841981"
    assert [s["action"] for s in result.trace] == [
        "plan", "map_hs_code", "check_data", "score_markets", "narrative"]
    assert result.ranking[0]["iso3"] == "USA"
    assert result.guard_warnings == []  # 叙事数字全部在台账内
    # 轨迹 JSON 可序列化（D5 前端要直接消费）
    json.dumps(result.to_json(), ensure_ascii=False)


def test_pipeline_unmappable_product(data, monkeypatch):
    import luopan.profile as prof_mod
    monkeypatch.setattr(prof_mod, "llm_lookup_hs6", lambda text: None)  # 禁用真 LLM 兜底
    wb, cty = data
    llm = FakeLlm(["计划"])
    r = MarketAgent(llm=llm, wb_records=wb, cty_records=cty).run("量子加密猫粮盆")
    assert r.error is not None and r.ranking is None
    assert r.trace[-1]["action"] == "map_hs_code"


def test_guard_extract_and_ledger():
    assert extract_numbers("进口14.15亿美元，2023年增长7.1%") == [14.15, 2023, 7.1]
    ledger = build_ledger("14.15亿美元 23.6% 7.1%")
    assert guard_check("进口14.15亿美元，份额23.6%", ledger) == []
    assert guard_check("进口20.99亿美元", ledger) == [20.99]
    assert guard_check("2023年排名第1，总分6.0", {"总分": None} and build_ledger("总分6.0")) == []


def test_followup_region_rerank(result, data):
    wb, cty = data
    agent = MarketAgent(llm=FakeLlm(["东南亚增速最快"]), wb_records=wb, cty_records=cty)
    out = agent.followup("只看东南亚还有哪些机会？", result)
    assert out["kind"] == "rerank_region"
    assert out["region"] == "东南亚"
    assert len(out["ranking"]) == 5
    assert all(r["iso3"] in {"IDN", "THA", "VNM", "MYS", "PHL"} for r in out["ranking"])
    json.dumps(out["trace"], ensure_ascii=False)


def test_followup_compare(result, data):
    wb, cty = data
    agent = MarketAgent(llm=FakeLlm(["美国规模更大，德国增速更高"]), wb_records=wb, cty_records=cty)
    out = agent.followup("美国和德国怎么选？", result)
    assert out["kind"] == "compare"
    assert {r["iso3"] for r in out["rows"]} == {"USA", "DEU"}
    # 排名称谓解析："第一名/第二名" 也要能触发对比
    out2 = agent.followup("第一名和第二名对比一下", result)
    assert out2["kind"] == "compare"
    assert {r["iso3"] for r in out2["rows"]} == {"USA", "DEU"}


def test_followup_explain_needs_no_llm(result, data):
    wb, cty = data
    agent = MarketAgent(llm=None, wb_records=wb, cty_records=cty)  # 不注入 LLM 也能解释
    out = agent.followup("中国份额这个指标是什么意思？", result)
    assert out["kind"] == "explain"
    assert "中国" in out["answer"]


def test_followup_freeform_guarded(result, data):
    wb, cty = data
    agent = MarketAgent(llm=FakeLlm(["Top1是6.999分的美国"]), wb_records=wb, cty_records=cty)
    out = agent.followup("第一名是谁？", result)
    assert out["kind"] == "freeform"
    assert out["guard"] == []
    agent_bad = MarketAgent(llm=FakeLlm(["德国市场高达99.99亿美元的进口"]), wb_records=wb, cty_records=cty)
    out_bad = agent_bad.followup("德国进口多少？", result)
    assert out_bad["guard"] == [99.99]  # 台账外数字被抓
