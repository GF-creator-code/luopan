"""真实出海案例库（公开资料整理）：相近品类/品牌事实 + 与评分结论的自动对照。

事实只收录公开可查的宽口径描述（公司年报、公开报道，检索 2026-10），
不使用无法溯源的精确数字；对照部分由代码计算（案例主攻市场 ∩ 我们 Top5），
零主观修饰——与 guard 的"可验证"原则一致。
"""

CASE_LIBRARY = {
    "850811": [  # 真空吸尘器/扫地机器人
        {"brand": "石头科技 Roborock", "relation": "同品类",
         "facts": "扫地机器人出海代表：据年报，境外收入占比近五成，以美国、德国等欧美市场为主力。",
         "markets": ["USA", "DEU"]},
        {"brand": "科沃斯 Ecovacs", "relation": "同品类（清洁电器）",
         "facts": "清洁电器出海龙头，海外以欧洲、美国为主要市场，多年位居海外销量前列（公开报道）。",
         "markets": ["DEU", "USA"]},
    ],
    "841981": [  # 加热饮品机/便携咖啡机
        {"brand": "Wacaco", "relation": "同品类（便携浓缩咖啡机）",
         "facts": "便携式浓缩咖啡机（Nanopresso/Picopresso 系列）代表品牌，主打欧美与东亚市场（公开报道）。",
         "markets": ["USA", "DEU", "JPN"]},
        {"brand": "HiBREW", "relation": "同品类（深圳出海品牌）",
         "facts": "深圳出身的咖啡机出海品牌，产品覆盖便携与台式，在亚马逊欧美多个站点为畅销款（公开报道）。",
         "markets": ["USA", "DEU"]},
    ],
    "852862": [  # 家用投影仪
        {"brand": "极米 XGIMI", "relation": "同品类（家用投影）",
         "facts": "国产家用投影出海代表，海外收入快速增长，以美国、欧洲与日本为主要市场（公司年报及公开报道）。",
         "markets": ["USA", "DEU", "JPN"]},
    ],
    "850980": [  # 其他家用机电器具（宠物智能用品等）
        {"brand": "小佩 PETKIT", "relation": "相近品类（宠物智能用品）",
         "facts": "宠物智能用品（智能喂食器、饮水机等）出海代表，产品覆盖欧美日等多个市场（公开报道）。",
         "markets": ["USA", "DEU", "JPN"]},
    ],
}


def cases_for(hs6):
    """返回该 HS6 品类的案例列表（可能为空）。"""
    return CASE_LIBRARY.get(hs6, [])


def alignment(case_markets, ranked):
    """案例主攻市场与完整排名的对照：返回 (落在我们Top5的, 其余及名次)。"""
    rank_of = {r["iso3"]: r["rank"] for r in ranked}
    top5 = set(list(rank_of)[:5]) if rank_of else set()
    hit = sorted(m for m in case_markets if m in top5)
    miss = sorted((m, rank_of.get(m)) for m in case_markets if m not in top5)
    return hit, miss
