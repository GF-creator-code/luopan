"""依据卡生成器单测：确定性、结构完整、零 LLM。"""
from luopan.explain import evidence_for


def _r(rank, iso3, name, **raw):
    base = {"scale": None, "scale_year": 2023, "china_share": None,
            "growth": None, "purchase_power": None, "digital": None,
            "logistics": None, "gdp_ppp": None, "urban": None, "tariff": None}
    base.update(raw)
    imputed = base.pop("imputed", [])
    sub = {"scale": 5.0, "growth": 5.0, "china_affinity": 5.0,
           "purchase_power": 5.0, "digital": 5.0, "logistics": 5.0}
    return {"rank": rank, "iso3": iso3, "name_zh": name, "total": 5.0,
            "sub": sub, "raw": base, "imputed": imputed}


def test_evidence_structure_and_content():
    ranked = [
        _r(1, "USA", "美国", scale=1.4e9, growth=0.067, china_share=0.236,
           purchase_power=86170, digital=90, logistics=3.8,
           gdp_ppp=80000, urban=83, tariff=3.3),
        _r(2, "DEU", "德国", scale=4.6e8, growth=0.089, china_share=0.118,
           purchase_power=52000, digital=91, logistics=4.1,
           gdp_ppp=62000, urban=78, tariff=1.6),
        _r(3, "THA", "泰国", scale=5e7, growth=-0.09, china_share=0.134,
           purchase_power=7000, digital=88, logistics=3.5, imputed=["growth"]),
    ]
    cards = evidence_for(ranked, price_tier="high")
    assert [c["rank"] for c in cards] == [1, 2, 3]
    usa = cards[0]
    assert usa["name"] == "美国"
    assert any("进口规模" in x and "14" in x for x in usa["reasons"])
    assert any("渠道对中国货接受度高" in x for x in usa["reasons"])
    assert any("愿付溢价" in x for x in usa["reasons"])  # 高价位 + 人均GDP 高
    assert any("PPP" in x and "印证" in x for x in usa["reasons"])
    assert any("RCEP" not in x for x in usa["reasons"])  # 美国非 RCEP
    tha = cards[2]
    assert any("收缩" in x for x in tha["reasons"])      # 负增速判读
    assert any("RCEP 成员" in x for x in tha["reasons"])  # 地理与协定
    assert any("中位数回填" in x for x in tha["reasons"])  # 缺失透明标注


def test_evidence_handles_missing_everything():
    cards = evidence_for([_r(1, "USA", "美国")])
    assert len(cards[0]["reasons"]) >= 1  # 至少增速缺失说明
    assert "主要驱动" in cards[0]["title"]
