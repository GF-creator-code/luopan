"""评分引擎单测：合成小数据 + 真实快照 fixture 的结构不变量与可复算断言。"""
import json
import math
from pathlib import Path

import pytest

from luopan.scoring import Weights, _minmax10, build_features, score_markets

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def _load(name):
    p = FIXTURES / name
    if not p.exists():
        pytest.skip("fixture 缺失: {}".format(p))
    return json.loads(p.read_text(encoding="utf-8"))["records"]


def _cty(hs6, reporter, year, partner, value):
    return {"hs6": hs6, "reporter": reporter, "year": year, "partner": partner,
            "flow": "M", "value_usd": value, "net_wgt": None}


def test_weights_sum_must_be_one():
    with pytest.raises(ValueError):
        Weights(scale=0.30)  # 和 = 1.05


def test_weights_negative_rejected():
    with pytest.raises(ValueError):
        Weights(growth=-0.1, scale=0.45)


def test_minmax_missing_imputes_median_and_flags():
    scores, imputed = _minmax10({"A": 100.0, "B": 50.0, "C": 0.0, "D": None})
    assert scores["A"] == 10.0
    assert scores["B"] == 5.0
    assert scores["C"] == 0.0
    assert imputed == {"D"}


def test_minmax_all_same_gives_flat_five():
    scores, imputed = _minmax10({"A": 7.0, "B": 7.0})
    assert scores == {"A": 5.0, "B": 5.0} and not imputed


def test_growth_and_china_share_synthetic():
    wb = [{"iso3": "USA", "indicator": "NY.GDP.PCAP.CD", "year": 2023, "value": 80000.0}]
    cty = [
        _cty("999999", 842, 2021, 0, 100.0),
        _cty("999999", 842, 2023, 0, 400.0),   # 两年 4 倍 → CAGR = 100%
        _cty("999999", 842, 2023, 156, 80.0),  # 自中国份额 0.8
    ]
    usa = build_features("999999", wb, cty)["USA"]
    assert math.isclose(usa["growth"], 1.0)
    assert math.isclose(usa["china_share"], 0.2)  # 80/400
    assert usa["scale"] == 400.0 and usa["scale_year"] == 2023
    assert usa["purchase_power"] == 80000.0
    assert usa["digital"] is None and usa["logistics"] is None


def test_china_share_none_when_world_zero():
    cty = [_cty("999999", 842, 2023, 0, 0), _cty("999999", 842, 2023, 156, 50.0)]
    usa = build_features("999999", [], cty)["USA"]
    assert usa["scale"] == 0.0
    assert usa["china_share"] is None
    assert usa["growth"] is None  # 单年无从算增速


def test_total_is_weighted_sum_of_published_subscores():
    wb = [
        {"iso3": "USA", "indicator": "NY.GDP.PCAP.CD", "year": 2023, "value": 80000.0},
        {"iso3": "DEU", "indicator": "NY.GDP.PCAP.CD", "year": 2023, "value": 52000.0},
    ]
    cty = [
        _cty("999999", 842, 2023, 0, 400.0),
        _cty("999999", 842, 2023, 156, 80.0),
        _cty("999999", 276, 2023, 0, 100.0),
        _cty("999999", 276, 2023, 156, 10.0),
    ]
    results = score_markets(build_features("999999", wb, cty))
    w = Weights()
    iso3s = {r["iso3"] for r in results}
    assert {"USA", "DEU"} <= iso3s  # 全市场池都参评，合成数据覆盖其中两国
    for r in results:
        expect = sum(getattr(w, k) * r["sub"][k] for k in r["sub"])
        assert math.isclose(r["total"], round(expect, 4), abs_tol=1e-9)
    usa = next(r for r in results if r["iso3"] == "USA")
    deu = next(r for r in results if r["iso3"] == "DEU")
    assert usa["rank"] < deu["rank"]  # 规模 400 vs 100、中国份额 0.2 vs 0.1 → 美国在前


def test_real_fixture_portable_coffee_deterministic():
    wb = _load("worldbank.json")
    cty = _load("comtrade.json")
    feats = build_features("841981", wb, cty)
    assert len(feats) == 21  # 21 个候选市场（中国除外）
    r1 = score_markets(feats)
    r2 = score_markets(build_features("841981", wb, cty))
    assert [x["iso3"] for x in r1] == [x["iso3"] for x in r2]
    assert [x["total"] for x in r1] == [x["total"] for x in r2]
    for x in r1:
        assert 0.0 <= x["total"] <= 10.0
    # 锚点：2026-10-12 抓取的美国 841981 自全球进口额（美元），防数据管道回归
    usa = next(x for x in r1 if x["iso3"] == "USA")
    assert usa["raw"]["scale_year"] == 2023
    assert abs(usa["raw"]["scale"] - 1414509898.316) < 1.0
