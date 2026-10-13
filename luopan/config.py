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

# 市场中文名 → ISO3（案例发现/追问解析共用）
NAME_TO_ISO3 = {info["name_zh"]: iso3 for iso3, info in COUNTRIES.items()}

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

# 两级品类目录（大类 → 细分品类）：细分项带 HS6。未预取快照的 HS6 首次分析
# 会按需实时抓取（约 1-2 分钟），之后走缓存。
CATEGORY_TREE = {
    "厨房与家居电器": [
        {"name": "咖啡机（便携/户外）", "hs6": "841981"},
        {"name": "电咖啡壶/茶饮机", "hs6": "851671"},
        {"name": "空气炸锅/电烤炉", "hs6": "851660"},
        {"name": "扫地机器人/吸尘器", "hs6": "850811"},
        {"name": "空气净化器", "hs6": "842139"},
        {"name": "电动牙刷/个护小电", "hs6": "850980"},
        {"name": "电吹风/电熨斗", "hs6": "851631"},
        {"name": "电动剃须刀", "hs6": "8510"},
    ],
    "家居与照明": [
        {"name": "家居照明/智能灯具", "hs6": "9405"},
        {"name": "家具/智能家具", "hs6": "9403"},
        {"name": "床品家纺", "hs6": "6302"},
        {"name": "抱枕与装饰布艺", "hs6": "6304"},
        {"name": "收纳整理用品", "hs6": "6307"},
    ],
    "餐厨与五金": [
        {"name": "塑料餐厨具", "hs6": "3924"},
        {"name": "陶瓷餐具", "hs6": "6912"},
        {"name": "玻璃杯具", "hs6": "7013"},
        {"name": "五金手工具", "hs6": "8205"},
        {"name": "园艺工具", "hs6": "8201"},
    ],
    "消费电子": [
        {"name": "家用投影仪", "hs6": "852862"},
        {"name": "便携电脑/平板", "hs6": "847130"},
        {"name": "智能手表/手环", "hs6": "851762"},
        {"name": "无线耳机/耳塞", "hs6": "851830"},
        {"name": "移动电源/户外储能", "hs6": "850760"},
        {"name": "智能手机", "hs6": "851713"},
        {"name": "手机保护壳/数码配件", "hs6": "392690"},
        {"name": "消费级无人机", "hs6": "8806"},
    ],
    "智能宠物": [
        {"name": "宠物智能用品（喂食器/饮水机）", "hs6": "850980"},
        {"name": "宠物食品（主粮/零食）", "hs6": "230910"},
        {"name": "宠物胸背带/牵引具", "hs6": "420100"},
    ],
    "户外与出行": [
        {"name": "电动滑板车/电动出行", "hs6": "871160"},
        {"name": "自行车/骑行整车", "hs6": "8712"},
        {"name": "露营灯具/户外照明", "hs6": "851310"},
        {"name": "便携储能/户外电源", "hs6": "850760"},
    ],
    "健身与运动": [
        {"name": "运动健身器材", "hs6": "950691"},
        {"name": "球类运动用品", "hs6": "950662"},
        {"name": "渔具", "hs6": "950790"},
    ],
    "美容与健康": [
        {"name": "美容仪/个护仪器", "hs6": "854370"},
        {"name": "按摩器具", "hs6": "901910"},
        {"name": "护肤与彩妆", "hs6": "3304"},
        {"name": "洗护发用品", "hs6": "3305"},
        {"name": "健康监测设备（血压计/血糖仪）", "hs6": "901890"},
    ],
    "服饰与配件": [
        {"name": "T恤与针织服装", "hs6": "6109"},
        {"name": "运动服饰", "hs6": "6211"},
        {"name": "鞋靴（运动/布面）", "hs6": "6404"},
        {"name": "箱包", "hs6": "4202"},
        {"name": "帽子", "hs6": "6505"},
        {"name": "仿真首饰", "hs6": "7117"},
        {"name": "眼镜", "hs6": "9004"},
    ],
    "玩具·游戏·母婴": [
        {"name": "玩具/智能玩具/潮玩", "hs6": "950300"},
        {"name": "游戏机与游戏设备", "hs6": "950450"},
        {"name": "节日派对用品", "hs6": "950510"},
        {"name": "婴儿推车与母婴用具", "hs6": "871500"},
    ],
    "食品与滋补": [
        {"name": "茶叶", "hs6": "0902"},
        {"name": "烘焙零食", "hs6": "1905"},
        {"name": "保健食品/蛋白粉", "hs6": "2106"},
    ],
    "汽车与车载": [
        {"name": "汽车零部件", "hs6": "8708"},
        {"name": "车载充电器/逆变器", "hs6": "850440"},
        {"name": "行车记录仪/车载摄像", "hs6": "852580"},
    ],
}
