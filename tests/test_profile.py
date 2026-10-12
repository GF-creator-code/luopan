"""产品档案与 HS6 映射单测。"""
import pytest

from luopan import envload
from luopan.profile import build_profile, lookup_hs6


def test_load_dotenv(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# 注释\nLLM_MODEL="glm-test"\nBAD_LINE\n\nLLM_BASE_URL=https://x.example\n', encoding="utf-8")
    monkeypatch.setenv("LLM_MODEL", "already-set")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    envload._loaded = False
    envload.load_dotenv(env)
    import os
    assert os.environ["LLM_MODEL"] == "already-set"       # 已存在的不覆盖
    assert os.environ["LLM_BASE_URL"] == "https://x.example"
    envload._loaded = False


def test_lookup_known_categories():
    assert lookup_hs6("想出口便携咖啡机") == "841981"
    assert lookup_hs6("扫地机器人 robot vacuum") == "850811"
    assert lookup_hs6("智能手表") == "851762"
    assert lookup_hs6("家用投影仪") == "852862"


def test_lookup_unknown_returns_none():
    assert lookup_hs6("量子加密猫粮盆") is None
    assert lookup_hs6("") is None


def test_build_profile_keyword():
    p = build_profile("家用投影仪 3000 元档")
    assert p is not None
    assert p.hs6 == "852862"
    assert p.matched_by == "keyword"
    assert p.hs_name_zh == "家用投影仪"
    assert p.price_tier == "mid"


def test_build_profile_manual_override():
    p = build_profile("随便写点什么", hs6="950300", price_tier="high")
    assert p.hs6 == "950300"
    assert p.matched_by == "manual"
    assert p.price_tier == "high"


def test_build_profile_failures():
    assert build_profile("未知产品", use_llm=False) is None  # 未配置 LLM 时不兜底
    assert build_profile("x", hs6="1234567") is None  # 非 6 位
    with pytest.raises(ValueError):
        build_profile("玩具", price_tier="超高端")
