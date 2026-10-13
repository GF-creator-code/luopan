"""案例库单测：检索与自动对照。"""
from luopan.cases import alignment, cases_for


def test_cases_cover_flagship_categories():
    assert len(cases_for("850811")) >= 2  # 扫地机器人：石头/科沃斯
    assert len(cases_for("841981")) >= 2  # 便携咖啡机：Wacaco/HiBREW
    assert cases_for("999999") == []      # 无案例品类安全返回空


def test_alignment_overlap_and_rank():
    ranked = [
        {"iso3": "USA", "rank": 1, "name_zh": "美国"},
        {"iso3": "DEU", "rank": 2, "name_zh": "德国"},
        {"iso3": "GBR", "rank": 3, "name_zh": "英国"},
        {"iso3": "FRA", "rank": 4, "name_zh": "法国"},
        {"iso3": "CAN", "rank": 5, "name_zh": "加拿大"},
        {"iso3": "JPN", "rank": 6, "name_zh": "日本"},
    ]
    hit, miss = alignment(["USA", "DEU", "JPN"], ranked)
    assert hit == ["DEU", "USA"]          # Top5 命中按字母序
    assert miss == [("JPN", 6)]           # 未命中带名次
