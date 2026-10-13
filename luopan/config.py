"""中心配置：市场池、World Bank 指标、Comtrade 品类预设与路径。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
FIXTURES_DIR = DATA_DIR / "fixtures"

WB_YEARS = (2019, 2024)

# 候选市场池：20 个主要消费国 + 中国（仅作供给端参照，不作评分目标）。
# cty = Comtrade reporter 数字码（UN 统计码，与 ISO 数字码基本一致，印度是 699 例外）
COUNTRIES = {
    "CHN": {"name_zh": "中国", "cty": 156},
    "USA": {"name_zh": "美国", "cty": 842},
    "DEU": {"name_zh": "德国", "cty": 276},
    "JPN": {"name_zh": "日本", "cty": 392},
    "GBR": {"name_zh": "英国", "cty": 826},
    "FRA": {"name_zh": "法国", "cty": 251},
    "KOR": {"name_zh": "韩国", "cty": 410},
    "AUS": {"name_zh": "澳大利亚", "cty": 364},
    "CAN": {"name_zh": "加拿大", "cty": 124},
    "NLD": {"name_zh": "荷兰", "cty": 528},
    "ITA": {"name_zh": "意大利", "cty": 380},
    "ESP": {"name_zh": "西班牙", "cty": 724},
    "MEX": {"name_zh": "墨西哥", "cty": 484},
    "BRA": {"name_zh": "巴西", "cty": 76},
    "IDN": {"name_zh": "印尼", "cty": 360},
    "THA": {"name_zh": "泰国", "cty": 764},
    "VNM": {"name_zh": "越南", "cty": 704},
    "MYS": {"name_zh": "马来西亚", "cty": 458},
    "PHL": {"name_zh": "菲律宾", "cty": 608},
    "IND": {"name_zh": "印度", "cty": 699},
    "SAU": {"name_zh": "沙特", "cty": 682},
    "ARE": {"name_zh": "阿联酋", "cty": 784},
}

WB_INDICATORS = {
    "NY.GDP.PCAP.CD": "人均GDP(美元)",
    "SP.POP.TOTL": "人口(人)",
    "IT.NET.USER.ZS": "互联网渗透率(%)",
    "LP.LPI.OVRL.XQ": "物流绩效指数LPI(1-5)",
    "NE.CON.PRVT.ZS": "居民消费占GDP(%)",
    "TM.TAX.MANF.SM.AR.ZS": "实施关税均值(制成品%)",
}

# 上下文指标：只进依据卡与风险提示，不参与评分（保持六维方法论稳定）
CONTEXT_INDICATORS = {
    "NY.GDP.PCAP.PP.CD": "人均GDP-PPP(国际元)",
    "SP.URB.TOTL.IN.ZS": "城镇化率(%)",
}

# CEPII GeoDist：北京—首都大圆距离（约值，四舍五入到百公里）；RCEP 成员（2022 年生效）
CEPII = {
    "JPN": {"distance_km": 2100, "rcep": True},
    "KOR": {"distance_km": 950, "rcep": True},
    "AUS": {"distance_km": 8900, "rcep": True},
    "IDN": {"distance_km": 5300, "rcep": True},
    "THA": {"distance_km": 3300, "rcep": True},
    "VNM": {"distance_km": 2300, "rcep": True},
    "MYS": {"distance_km": 4500, "rcep": True},
    "PHL": {"distance_km": 2900, "rcep": True},
    "USA": {"distance_km": 11100, "rcep": False},
    "CAN": {"distance_km": 10500, "rcep": False},
    "MEX": {"distance_km": 12500, "rcep": False},
    "BRA": {"distance_km": 16900, "rcep": False},
    "DEU": {"distance_km": 7400, "rcep": False},
    "GBR": {"distance_km": 8100, "rcep": False},
    "FRA": {"distance_km": 8200, "rcep": False},
    "NLD": {"distance_km": 7900, "rcep": False},
    "ITA": {"distance_km": 8100, "rcep": False},
    "ESP": {"distance_km": 9200, "rcep": False},
    "IND": {"distance_km": 3800, "rcep": False},
    "SAU": {"distance_km": 6200, "rcep": False},
    "ARE": {"distance_km": 5900, "rcep": False},
}

# 区域约束（追问"只看东南亚"等）；必须覆盖全部 21 个候选市场
REGIONS = {
    "北美": ["USA", "CAN"],
    "欧洲": ["DEU", "GBR", "FRA", "NLD", "ITA", "ESP"],
    "东亚": ["JPN", "KOR"],
    "东南亚": ["IDN", "THA", "VNM", "MYS", "PHL"],
    "南亚": ["IND"],
    "中东": ["SAU", "ARE"],
    "大洋洲": ["AUS"],
    "拉美": ["MEX", "BRA"],
}

# 常见出海品类预设（离线 demo 兜底）。years = 抓取计划（preview 每次调用只收 1 个年份）；
# 全部按预算跨天续跑，先保旗舰案例 841981（便携咖啡机）三年完整。
HS_PRESETS = {
    "841981": {"name_zh": "加热饮品机(便携咖啡机)", "years": (2021, 2022, 2023)},
    "850811": {"name_zh": "真空吸尘器(含扫地机器人)", "years": (2023,)},
    "852862": {"name_zh": "家用投影仪", "years": (2023,)},
    "850980": {"name_zh": "其他家用机电器具(宠物智能用品等)", "years": (2023,)},
    "851671": {"name_zh": "电咖啡壶", "years": (2023,)},
    "950300": {"name_zh": "玩具(含智能玩具)", "years": (2023,)},
    "847130": {"name_zh": "便携式电脑", "years": (2023,)},
    "851762": {"name_zh": "智能手表等通信设备", "years": (2023,)},
}
