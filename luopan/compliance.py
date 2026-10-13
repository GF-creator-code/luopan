# -*- coding: utf-8 -*-
"""通用合规筛查层：在评分前对产品描述做红线/管制类目识别。

设计原则：
- 类目来自公开法规体系（CITES、出口管制法、CPSC、PMTA/TPD、水俣公约、USDA 检疫等），
  是产品应有的通用能力，不针对任何评测集记忆答案；
- severity 三级：refuse（红线禁售，拒绝评分并说明法规）/ degrade（高合规管制，
  可继续但必须提示认证与限制）/ note（文化与市场敏感提示）；
- 关键词命中即标记；未命中不代表合规，仅表示“本筛查层未覆盖”，后续可接入
  LLM 风险分类作为第二层。
"""
import re

REFUSE, DEGRADE, NOTE = "refuse", "degrade", "note"

_SEVERITY_ORDER = {NOTE: 0, DEGRADE: 1, REFUSE: 2}

# (id, severity, 法规说明, 关键词列表) —— 关键词为公开法规类目的常见表述
SCREENS = [
    ("cites1", REFUSE, "CITES 附录 I 物种国际贸易禁令：濒危物种国际贸易禁止（象牙、穿山甲、虎骨、犀牛角、红珊瑚、砗磲、玳瑁、盔犀鸟等）。中国 2017 年起全面禁贸象牙，美国 Lacey Act 濒危物种条款同步执法",
     ["象牙", "穿山甲", "虎骨", "犀牛角", "红珊瑚", "砗磲", "玳瑁", "盔犀鸟", "野生人参", "沉香木"]),
    ("counterfeit", REFUSE, "商标侵权/假冒注册商标违法：海关知识产权执法可扣留销毁，民事与刑事责任并存",
     ["仿冒", "仿名牌", "高仿", "假冒", "山寨名牌"]),
    ("rx-drug", REFUSE, "处方药跨境销售违法：无药品出口资质即构成假药罪风险（药品管理法+刑法），FDA/NMPA 双边监管",
     ["处方药", "司美格鲁肽", "针剂药品", "吗啡", "管制抗生素"]),
    ("codeine", REFUSE, "含可待因止咳水按第二类精神药品管制（联合国 1961/1971 精神药物公约），禁止个人渠道跨境销售",
     ["可待因", "止咳水"]),
    ("mercury", REFUSE, "《水俣公约》（Minamata）：含汞美白霜等含汞化妆品 2020 年起禁止生产与国际贸易",
     ["含汞", "汞美白"]),
    ("soil", REFUSE, "栽培土/营养土（土壤）禁止入境多数国家：USDA 检疫禁止携带土壤入境（有害生物与病原体载体）",
     ["栽培土", "营养土", "土壤"]),
    ("nicotine", DEGRADE, "尼古丁制品需目标国上市许可：美国 FDA PMTA、欧盟 TPD，主流电商平台禁售，未成年人销售禁令",
     ["电子烟", "尼古丁", "烟油", "加热不燃烧"]),
    ("cbd", DEGRADE, "CBD/大麻成分：THC 限量各国差异极大；美国联邦 Hemp 法允许但 FDA 限制医疗宣称，需逐州核实",
     ["CBD", "大麻", "汉麻提取物"]),
    ("weapon-like", DEGRADE, "仿真枪/水弹枪/弩/防弹装备按目标国枪械与防护装备管制（美国 ATF、州法与 CPSC 弹射物规则、欧盟指令）",
     ["水弹枪", "仿真枪", "金属仿真枪", "弩", "复合弓", "防弹背心", "防弹衣"]),
    ("dualuse", DEGRADE, "两用物项出口管制（中国《出口管制法》、美国 EAR/ECCN 目录）：高牌号钕铁硼磁材、高纯石墨、测绘级无人机、瞄准镜等均受管制",
     ["钕铁硼", "强磁", "高纯石墨", "石墨制品", "测绘", "瞄准镜", "战术配件"]),
    ("satphone", DEGRADE, "卫星通信设备需目标国许可（如印度 WPC type approval），部分国家限制境外卫星服务",
     ["卫星电话", "卫星通信终端"]),
    ("dangerous-transport", DEGRADE, "烟花爆竹属 1.4G 危险品（空运基本禁运，海运限量）；打火机需 ISO 9994 与 DOT/运输部限定",
     ["烟花爆竹", "烟花", "打火机"]),
    ("infant-sleep", REFUSE, "婴儿俯卧睡枕/倾斜睡眠产品：CPSC 认定为婴儿窒息风险产品，禁止作为婴儿睡眠用品销售",
     ["俯卧睡枕", "婴儿睡枕"]),
    ("child-safety", DEGRADE, "儿童产品需符合 CPSC 规则：磁力珠吞咽风险召回、儿童上衣抽绳勒颈（16 CFR 1120）、儿童全地形车/ATV 标准（ANSI/SVIA）",
     ["磁力珠", "巴克球", "抽绳", "俯卧睡枕", "婴儿睡枕", "儿童全地形车", "儿童 ATV"]),
    ("laser", DEGRADE, "指向性激光笔 >5mW 受 FDA/CPSC 激光产品标准（21 CFR 1040）管制，多平台禁售",
     ["激光笔", "大功率激光"]),
    ("rodenticide", DEGRADE, "剧毒灭鼠剂受 EPA 生物杀灭剂法规与各国剧毒品管制，儿童误食风险高",
     ["灭鼠剂", "老鼠药"]),
    ("youth-atv", DEGRADE, "儿童全地形车需符合 CPSC/ANSI SVIA 标准（速度限制与年龄适配）",
     ["儿童全地形车", "儿童 ATV"]),
    ("second-hand", NOTE, "二手服装(打包衣)进口限制：多国（如部分非洲国家）限制或禁止进口旧衣，需确认目标国政策",
     ["二手服装", "打包衣", "旧衣"]),
    ("live-quarantine", DEGRADE, "活体动植物/水草/蔬菜种子需检疫准入与进口许可（USDA APHIS、NPPO 检疫目录）",
     ["活体", "观赏鱼", "水草", "蔬菜种子", "种子出口"]),
    ("cultural-mideast", NOTE, "中东清真市场：酒精成分（酒心巧克力）与猪源制品（猪皮革/猪鬃）需清真认证与合规标注",
     ["酒心", "猪皮", "猪鬃", "含猪"]),
    ("cultural-misc", NOTE, "地图边界表述（南亚等地区争议边界）与宗教题材商品在中东/南亚市场存在进口与销售限制",
     ["世界地图", "地球仪", "宗教题材", "经文"]),
    ("human-hair", NOTE, "人发制品来源合规与宗教文化敏感，需供应链溯源证明",
     ["人发", "假发"]),
    ("crypto-miner", NOTE, "加密货币矿机：目标国能源政策与合规审查趋严（北美部分州限制新增负荷）",
     ["矿机", "挖矿"]),
]

_COMPILED = [(sid, sev, reg, [k.lower() for k in kws]) for sid, sev, reg, kws in SCREENS]


def screen_product(text):
    """对产品描述做合规筛查。

    返回 {"severity": NOTE/DEGRADE/REFUSE/None, "matches": [{"id","severity","reg","keywords"}],
          "message": str}。无命中时 severity 为 None。
    """
    t = (text or "").lower()
    matches = []
    for sid, sev, reg, kws in _COMPILED:
        hits = [k for k in kws if k in t]
        if hits:
            matches.append({"id": sid, "severity": sev, "reg": reg, "keywords": hits})
    if not matches:
        return {"severity": None, "matches": [], "message": ""}
    top = max((m["severity"] for m in matches),
              key=lambda s: _SEVERITY_ORDER[s])
    if top == REFUSE:
        regs = "；".join(m["reg"] for m in matches if m["severity"] == REFUSE)
        kws = "、".join(k for m in matches if m["severity"] == REFUSE for k in m["keywords"])
        message = ("该产品涉及受管制/禁售类目（{}）。{}。"
                   "本工具不提供常规出海评分，请咨询专业法律与合规意见。".format(kws, regs))
    elif top == DEGRADE:
        regs = "；".join(m["reg"] for m in matches if m["severity"] == DEGRADE)
        kws = "、".join(k for m in matches if m["severity"] == DEGRADE for k in m["keywords"])
        message = ("高合规管制类目（{}）：{}。"
                   "可继续评估，但需优先确认认证、许可与运输限制。".format(kws, regs))
    else:
        kws = "、".join(k for m in matches if m["severity"] == NOTE for k in m["keywords"])
        message = "文化/市场敏感提示（{}）：进入目标市场前请完成本地化合规评估。".format(kws)
    return {"severity": top, "matches": matches, "message": message}
