# -*- coding: utf-8 -*-
"""出海罗盘参赛作品 PPT 构建脚本（pptx skill 规范）。

20 页 · 16:9（13.333×7.5in）· 微软雅黑 · 深浅三明治 · 原生图表 · 无色条无下划线。
数据全部来自 data/fixtures（确定性评分输出）与 assets_ppt/data_841981.json。
"""
import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt, Emu

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "assets_ppt" / "data_841981.json").read_text(encoding="utf-8"))
SHOT = ROOT / "assets_ppt"
OUT = ROOT / "output" / "出海罗盘_参赛作品_v1.pptx"

# ---- 调色板（skill §2：BACKGROUND → PRIMARY → ACCENT，常量唯一定义处）----
BG_DARK = RGBColor(0x16, 0x32, 0x4F)   # 深海蓝：封面/封底
BG_LIGHT = RGBColor(0xFF, 0xFF, 0xFF)  # 白：内容页
PRIMARY = RGBColor(0x1D, 0x5C, 0x96)   # 品牌蓝
NAVY = RGBColor(0x16, 0x32, 0x4F)
ACCENT = RGBColor(0xC8, 0x92, 0x2A)    # 罗盘金（仅 5-10% 面积）
TEXT = RGBColor(0x1E, 0x25, 0x30)
MUTED = RGBColor(0x5C, 0x6B, 0x7A)
LINE = RGBColor(0xE6, 0xEA, 0xF0)
TINT = RGBColor(0xED, 0xF1, 0xF6)      # 主色浅底
GOLD_TINT = RGBColor(0xFF, 0xF6, 0xE5)

FONT = "微软雅黑"
W, H, M = 13.333, 7.5, 0.5

RANK = {x["name"]: x for x in DATA["ranking"]}
TREND = DATA["trend_top5"]

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


# ---- 基础 helper ----
def set_font(run, size, bold=False, color=TEXT):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", FONT)


def add_text(slide, x, y, w, h, lines, size=14, bold=False, color=TEXT,
             align=PP_ALIGN.LEFT, space_after=6):
    """lines: str 或 [(text, bold, color, size), ...]"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    if isinstance(lines, str):
        lines = [(lines, bold, color, size)]
    for i, (t, b, c, s) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = t
        set_font(run, s, b, c)
    return tb


def dark_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG_DARK
    return s


def light_slide(sec_no, sec_name, page_no, title, kicker=None):
    """内容页：超大节号 motif + 金色小节标签 + 标题 + 页码。"""
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG_LIGHT
    # 超大节号（签名 motif）
    num = s.shapes.add_textbox(Inches(M), Inches(0.32), Inches(1.35), Inches(1.0))
    p = num.text_frame.paragraphs[0]
    r = p.add_run(); r.text = sec_no
    set_font(r, 44, True, RGBColor(0xD7, 0xDF, 0xE8))
    # 金色小节标签 + 标题
    tag = s.shapes.add_textbox(Inches(1.75), Inches(0.42), Inches(9.5), Inches(0.34))
    p = tag.text_frame.paragraphs[0]
    r = p.add_run(); r.text = sec_name
    set_font(r, 12, True, ACCENT)
    t = s.shapes.add_textbox(Inches(1.75), Inches(0.72), Inches(10.8), Inches(0.62))
    p = t.text_frame.paragraphs[0]
    r = p.add_run(); r.text = title
    set_font(r, 25, True, NAVY)
    # 页码
    pn = s.shapes.add_textbox(Inches(12.55), Inches(7.08), Inches(0.6), Inches(0.3))
    p = pn.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r = p.add_run(); r.text = str(page_no)
    set_font(r, 11, False, MUTED)
    if kicker:
        k = s.shapes.add_textbox(Inches(1.75), Inches(1.34), Inches(11.0), Inches(0.4))
        p = k.text_frame.paragraphs[0]
        r = p.add_run(); r.text = kicker
        set_font(r, 12.5, False, MUTED)
    return s


def source_line(slide, text, y=6.95):
    sl = slide.shapes.add_textbox(Inches(M), Inches(y), Inches(9.5), Inches(0.32))
    p = sl.text_frame.paragraphs[0]
    r = p.add_run(); r.text = text
    set_font(r, 11, False, MUTED)


def style_chart(chart, legend=False):
    chart.has_title = False
    chart.font.size = Pt(12)
    chart.font.name = FONT
    try:
        chart.font.color.rgb = MUTED
    except Exception:
        pass
    if legend:
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        try:
            chart.legend.font.size = Pt(11)
        except Exception:
            pass
    else:
        chart.has_legend = False


def card(slide, x, y, w, h, tint=TINT):
    """浅底卡片（skill 允许的底色区分法，无边条）。"""
    from pptx.enum.shapes import MSO_SHAPE
    sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sp.adjustments[0] = 0.06
    sp.fill.solid()
    sp.fill.fore_color.rgb = tint
    sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


# ================= 1 封面（深蓝） =================
s = dark_slide()
add_text(s, M + 0.2, 1.15, 12, 0.4, [("第二届 · 通用赛道 ｜ 命题领域：出海", True, ACCENT, 14)])
add_text(s, M + 0.2, 1.7, 12, 1.1, [("出海罗盘", True, RGBColor(0xFF, 0xFF, 0xFF), 60)])
add_text(s, M + 0.2, 2.9, 12, 0.5, [("GlobalCompass · 全球业务智能决策智能体", False,
                                     RGBColor(0xB9, 0xC7, 0xD6), 17)])
# 分隔留白 + 三段价值主张
add_text(s, M + 0.2, 4.0, 12, 0.45,
         [("公开权威数据 × 确定性评分 × 可验证 AI 解读", True, RGBColor(0xFF, 0xFF, 0xFF), 20)])
for i, (t, sub) in enumerate([
        ("世界银行 WDI", "宏观与营商环境指标"),
        ("UN Comtrade", "HS6 品类贸易数据"),
        ("数字台账守卫", "AI 数字逐条核验")]):
    x = M + 0.2 + i * 4.1
    add_text(s, x, 5.1, 3.9, 0.4, [(t, True, RGBColor(0xFF, 0xFF, 0xFF), 15)])
    add_text(s, x, 5.52, 3.9, 0.4, [(sub, False, RGBColor(0xA9, 0xBA, 0xCC), 12)])
add_text(s, M + 0.2, 6.85, 12, 0.35,
         [("数据来源：世界银行 WDI · UN Comtrade（检索 2026-10）", False,
           RGBColor(0x8C, 0x9F, 0xB2), 11)])

# ================= 2 §一 背景与说明 =================
s = light_slide("01", "作品背景与说明", 2, "出海第一问：先去哪个国家卖？")
add_text(s, 1.75, 1.6, 11, 0.6,
         [("中小卖家出海的第一道题，长期靠“拍脑袋”和二手报告。", True, NAVY, 17)])
rows = [
    ("拍脑袋决策", "凭感觉选国家，缺乏数据支撑，试错成本极高"),
    ("二手报告贵且慢", "行业报告动辄数万元、周级交付，且口径不透明"),
    ("通用大模型直接问", "回答流畅，但数字凭模型记忆生成，无法溯源与复算"),
]
y = 2.5
for t, d in rows:
    add_text(s, 1.75, y, 2.6, 0.4, [(t, True, PRIMARY, 15)])
    add_text(s, 4.5, y, 8.2, 0.4, [(d, False, TEXT, 13.5)])
    y += 0.62
add_text(s, 1.75, 4.6, 11, 0.4,
         [("出海罗盘的主张：把「选市场」变成一次可复算的数据分析。", True, NAVY, 16)])
add_text(s, 1.75, 5.1, 11, 0.9,
         [("以便携咖啡机（HS 841981）为例：2023 年美国自全球进口 14.15 亿美元、"
           "中国份额 23.6%、年均增速 6.7%（UN Comtrade，检索 2026-10）。"
           "这些数字不应来自模型记忆，而应来自权威数据库的实时查询与确定性计算。", False, TEXT, 13)])
source_line(s, "数据来源：UN Comtrade Public Preview，HS 841981，检索 2026-10")

# ================= 3 §二-1 数据来源 =================
s = light_slide("02", "数据收集与处理 · 来源", 3, "三个公开权威渠道，全部可溯源")
tbl_data = [
    ["渠道", "提供内容", "权威性与时效性"],
    ["世界银行 WDI API", "人均GDP、人口、互联网渗透率、物流绩效 LPI、关税等 8 项指标（2019-2024）",
     "国际组织官方数据库，2026-10-08 更新"],
    ["UN Comtrade API", "HS6 细分品类进口额、年度序列、中国份额（21 市场 × 多年）",
     "联合国官方贸易统计库"],
    ["CEPII GeoDist", "北京—首都大圆距离、RCEP 成员标识", "国际经济学界标准地理数据库"],
]
tb = s.shapes.add_table(4, 3, Inches(1.75), Inches(1.7), Inches(10.9), Inches(2.6)).table
tb.columns[0].width = Inches(2.4)
tb.columns[1].width = Inches(4.9)
tb.columns[2].width = Inches(3.6)
for r_i, row in enumerate(tbl_data):
    for c_i, cell_text in enumerate(row):
        cell = tb.cell(r_i, c_i)
        cell.text = cell_text
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                set_font(run, 12.5 if r_i else 13, r_i == 0,
                         RGBColor(0xFF, 0xFF, 0xFF) if r_i == 0 else TEXT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r_i == 0 else (TINT if r_i % 2 else BG_LIGHT)
add_text(s, 1.75, 4.65, 11, 0.75,
         [("全部为免密钥/开放授权接口：无爬虫、无合规风险；检索日期统一标注，"
           "满足匿名评审的数据合规要求。", False, TEXT, 13)])
source_line(s, "接口实测：World Bank API v2 / UN Comtrade Public Preview（2026-10-12 连通性验证通过）")

# ================= 4 §二-2 知识库内容 =================
s = light_slide("02", "数据收集与处理 · 知识库", 4, "把“会查数据”沉淀为三层知识库")
blocks = [
    ("两级品类目录", "12 大类 / 58 细分品类，每个细分挂真实 6 位 HS 编码；"
     "未预取品类首次分析自动联网补数"),
    ("三级品类识别", "关键词校对表（毫秒级）→ AI 拆解匹配（组合套件逐部件映射）→ 人工兜底；"
     "识别过程全程可视化"),
    ("真实案例库", "相近品类/品牌公开事实 + 与评分排名的自动对照；"
     "来源仅收公司年报与公开报道"),
]
x = 1.75
for t, d in blocks:
    card(s, x, 1.8, 3.5, 2.9)
    add_text(s, x + 0.25, 2.05, 3.0, 0.5, [(t, True, PRIMARY, 15)])
    add_text(s, x + 0.25, 2.6, 3.05, 2.0, [(d, False, TEXT, 12.5)])
    x += 3.7
add_text(s, 1.75, 5.0, 11, 0.8,
         [("知识库的价值：让「任何小众品类」都能被结构化理解——"
           "例如“胶片翻拍设备”会被拆解为片夹（901090）、冲洗设备（901010）等部件并逐一定编码。", False, TEXT, 13)])
source_line(s, "品类目录与识别规则均已版本化管理，见代码仓库 luopan/config.py、luopan/profile.py")

# ================= 5 §二-3 预处理与利用（管线图） =================
s = light_slide("02", "数据收集与处理 · 管线", 5, "一条可复现的数据管线")
steps = [("抓取", "官方 API\n限速+退避"), ("缓存", "本地 JSON\n断网可用"), ("校验", "编码/缺失\n显式标注"),
         ("评分", "确定性代码\n同输入同输出"), ("守卫", "AI 数字\n台账核验"), ("报告", "带来源\n可复算")]
x = 1.75
for i, (t, d) in enumerate(steps):
    card(s, x, 2.1, 1.62, 1.5, TINT if i % 2 == 0 else GOLD_TINT)
    add_text(s, x + 0.12, 2.28, 1.4, 0.4, [(t, True, NAVY, 15)])
    add_text(s, x + 0.12, 2.78, 1.42, 0.7, [(d.replace("\n", "，"), False, MUTED, 10.5)])
    if i < 5:
        arr = s.shapes.add_textbox(Inches(x + 1.6), Inches(2.62), Inches(0.35), Inches(0.4))
        p = arr.text_frame.paragraphs[0]
        r = p.add_run(); r.text = "→"
        set_font(r, 16, True, ACCENT)
    x += 1.95
add_text(s, 1.75, 4.1, 11, 0.9,
         [("工程细节即可信度：请求级限速与 429/503 退避、非 JSON 网关错误自动重试、"
           "双 LLM 通道自动切换、全量响应落盘缓存。同一份输入永远得到同一份排名。", False, TEXT, 13.5)])
add_text(s, 1.75, 5.15, 11, 0.9,
         [("为什么这样做：数据管线的每一层都可能引入偏差，我们把每一层都变成"
           "「显式、可检查」的步骤——这是“可落地性”的工程基础。", True, NAVY, 13.5)])

# ================= 6 §二-4 趋势图（原生 LINE） =================
s = light_slide("02", "数据收集与处理 · 贸易趋势", 6, "便携咖啡机：Top5 市场进口额趋势")
years = ["2021", "2022", "2023"]
cd = CategoryChartData()
cd.categories = years
names = {x["iso3"]: x["name"] for x in DATA["ranking"][:5]}
for iso3, series in TREND.items():
    cd.add_series(names[iso3], tuple(series.get(y, 0) for y in years))
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(1.75), Inches(1.7),
                        Inches(10.9), Inches(4.5), cd)
chart = gf.chart
style = chart
chart.has_title = False
chart.font.size = Pt(12)
colors = [ACCENT, PRIMARY, RGBColor(0x4A, 0x90, 0xC4), RGBColor(0x7F, 0xA8, 0xD0), RGBColor(0xB4, 0xCB, 0xE2)]
for i, ser in enumerate(chart.series):
    ser.format.line.color.rgb = colors[i % len(colors)]
    ser.format.line.width = Pt(2.4)
    ser.smooth = False
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(11)
source_line(s, "数据来源：UN Comtrade HS 841981 自全球进口额（亿美元），检索 2026-10")

# ================= 7 §二-5 数据质量治理 =================
s = light_slide("02", "数据收集与处理 · 质量治理", 7, "四种真实故障，四种显式应对")
g_rows = [
    ("接口限流 429/503", "请求级限速 + 指数退避重试 + 全量缓存跨天续跑"),
    ("新品类无历史数据", "按需实时补数（21 市场 ≈ 100 秒），缺失市场显式标注"),
    ("维度数据缺失", "禁止黑箱编造：中位数回填 + 界面显式标注“待补维度”"),
    ("网关异常响应", "非 JSON/SSE 双格式兼容 + 双 LLM 通道自动切换"),
]
y = 1.75
for t, d in g_rows:
    card(s, 1.75, y, 10.9, 0.92)
    add_text(s, 2.0, y + 0.14, 3.4, 0.6, [(t, True, PRIMARY, 14)])
    add_text(s, 5.6, y + 0.14, 6.8, 0.66, [(d, False, TEXT, 12.5)])
    y += 1.16
add_text(s, 1.75, 6.5, 11, 0.4,
         [("原则：数据缺失永远“显式标注”，绝不静默编造——这是可验证性的底线。", True, NAVY, 13.5)])

# ================= 8 §三-1 方法论 =================
s = light_slide("03", "分析过程 · 方法选择", 8, "六维加权评分：把“选市场”变成可复算的模型")
m_tbl = [
    ["维度", "指标", "权重", "来源"],
    ["市场规模", "该 HS6 自全球进口额（最新年）", "25%", "UN Comtrade"],
    ["市场增速", "进口额首末年复合年均增速", "20%", "UN Comtrade"],
    ["渠道接受度", "自中国进口 ÷ 自全球进口", "20%", "UN Comtrade"],
    ["购买力", "人均 GDP", "15%", "世界银行 WDI"],
    ["数字渠道", "互联网渗透率", "10%", "世界银行 WDI"],
    ["物流就绪", "物流绩效指数 LPI", "10%", "世界银行 WDI"],
]
tb = s.shapes.add_table(7, 4, Inches(1.75), Inches(1.65), Inches(7.2), Inches(4.3)).table
tb.columns[0].width = Inches(1.7)
tb.columns[1].width = Inches(3.3)
tb.columns[2].width = Inches(0.9)
tb.columns[3].width = Inches(1.3)
for r_i, row in enumerate(m_tbl):
    for c_i, cell_text in enumerate(row):
        cell = tb.cell(r_i, c_i)
        cell.text = cell_text
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                set_font(run, 12 if r_i else 12.5, r_i == 0 or c_i == 2,
                         RGBColor(0xFF, 0xFF, 0xFF) if r_i == 0 else TEXT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r_i == 0 else (TINT if r_i % 2 else BG_LIGHT)
add_text(s, 9.3, 1.75, 3.4, 4.2,
         [("为什么是这六个维度", True, PRIMARY, 15),
          ("规模+增速：蛋糕多大、还在不在长大", False, TEXT, 12.5),
          ("渠道接受度：当地卖不卖中国货", False, TEXT, 12.5),
          ("购买力：与价位段匹配", False, TEXT, 12.5),
          ("数字+物流：跨境履约基础", False, TEXT, 12.5),
          (" ", False, TEXT, 6),
          ("权重全部用户可调，实时重排；", False, TEXT, 12.5),
          ("并列分按国家代码定序，同输入必同输出。", False, TEXT, 12.5)])
source_line(s, "关税不入评分模型，仅在风险提示层呈现（世界银行制成品关税均值）")

# ================= 9 §三-2 分析流程 =================
s = light_slide("03", "分析过程 · 流程", 9, "五步智能体流程：每一步都看得见")
steps = [("plan", "规划", "生成分析计划"), ("map", "品类定位", "HS 编码三级识别"),
         ("check", "覆盖检查", "缺口自动补数"), ("score", "六维评分", "确定性计算"),
         ("narrate", "守卫叙事", "数字台账核验")]
x = 1.75
for i, (en, cn, d) in enumerate(steps):
    card(s, x, 2.0, 2.0, 1.7, TINT)
    add_text(s, x + 0.15, 2.15, 1.8, 0.35, [(en, True, ACCENT, 11)])
    add_text(s, x + 0.15, 2.5, 1.8, 0.45, [(cn, True, NAVY, 15)])
    add_text(s, x + 0.15, 3.0, 1.8, 0.6, [(d, False, MUTED, 10.5)])
    if i < 4:
        arr = s.shapes.add_textbox(Inches(x + 2.0), Inches(2.6), Inches(0.4), Inches(0.4))
        p = arr.text_frame.paragraphs[0]
        r = p.add_run(); r.text = "→"
        set_font(r, 18, True, ACCENT)
    x += 2.32
add_text(s, 1.75, 4.1, 11, 0.9,
         [("分工红线：LLM 只负责计划措辞、品类映射与台账内叙事；"
           "评分、排名、依据全部由确定性代码完成。", False, TEXT, 13.5)])
add_text(s, 1.75, 4.9, 11, 0.9,
         [("叙事层的每个数字都要通过“数字台账守卫”——不在台账中的数字会被显式标警。"
           "这正是章程要求的“可验证智能体交互能力”的工程实现。", True, NAVY, 13.5)])

# ================= 10 §三-3 数据实例（Top10 BAR） =================
s = light_slide("03", "分析过程 · 数据实例", 10, "便携咖啡机：21 个候选市场评分")
top10 = DATA["ranking"][:10]
cd = CategoryChartData()
cd.categories = [x["name"] for x in top10]
cd.add_series("综合总分", tuple(x["total"] for x in top10))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(1.75), Inches(1.6),
                        Inches(7.3), Inches(5.0), cd)
chart = gf.chart
chart.has_title = False
chart.font.size = Pt(11)
chart.has_legend = False
plot = chart.plots[0]
plot.vary_by_categories = True
ser = plot.series[0]
ser.format.fill.solid()
ser.format.fill.fore_color.rgb = PRIMARY
pt0 = ser.points[0]
pt0.format.fill.solid()
pt0.format.fill.fore_color.rgb = ACCENT
plot.has_data_labels = True
plot.data_labels.font.size = Pt(10.5)
plot.data_labels.number_format = "0.00"
plot.data_labels.number_format_is_linked = False
va = chart.value_axis
va.has_title = True
va.axis_title.text_frame.text = "综合总分（0-10）"
for p_ in va.axis_title.text_frame.paragraphs:
    for r_ in p_.runs:
        set_font(r_, 11, False, MUTED)
ca = chart.category_axis
ca.has_title = True
ca.axis_title.text_frame.text = "候选市场"
for p_ in ca.axis_title.text_frame.paragraphs:
    for r_ in p_.runs:
        set_font(r_, 11, False, MUTED)
source_line(s, "数据来源：UN Comtrade HS 841981（2023 年进口额与 2021-2023 增速）+ 世界银行 WDI，检索 2026-10")
add_text(s, 9.35, 1.8, 3.3, 4.6,
         [("怎么读这张图", True, PRIMARY, 14),
          ("美国以 6.999 分居首：规模、购买力、渠道接受度三项全面领先。", False, TEXT, 12),
          (" ", False, TEXT, 6),
          ("马来西亚是典型“小而快”市场：规模仅 0.64 亿美元，但 28.3% 的增速与"
           "28.1% 的中国份额把它推进前五。", False, TEXT, 12),
          (" ", False, TEXT, 6),
          ("排序由六维加权决定，不是单一指标排序——换权重即换视角。", False, TEXT, 12)])

# ================= 11 §三-4 可信度论证 =================
s = light_slide("03", "分析过程 · 可信度", 11, "三道防线，让每个数字都站得住")
lines = [
    ("第一道：确定性评分", "评分与排名 100% 由代码完成（55 项自动化测试），"
     "同输入必同输出，任何人可复算"),
    ("第二道：来源标注", "报告与界面中的每个数字都带年份与来源"
     "（UN Comtrade / 世界银行），检索日期统一标注"),
    ("第三道：数字台账守卫", "AI 生成的每个数字都要与“事实清单+用户原文”台账比对，"
     "台账外的数字会被显式标警"),
]
y = 1.7
for t, d in lines:
    card(s, 1.75, y, 10.9, 1.15)
    add_text(s, 2.0, y + 0.16, 3.6, 0.8, [(t, True, PRIMARY, 14.5)])
    add_text(s, 5.8, y + 0.16, 6.7, 0.85, [(d, False, TEXT, 12.5)])
    y += 1.38
add_text(s, 1.75, 6.1, 11, 0.6,
         [("实测：守卫曾两次捕获模型自行推算的数字并标警——机制在真实运行中被验证有效。",
           True, NAVY, 13.5)])

# ================= 12 §四-1 创新点 =================
s = light_slide("04", "创新性与独特视角 · 创新点", 12, "三个创新点")
inns = [
    ("数字台账守卫", "AI 输出的每个数字与“事实清单+用户原文”台账逐条比对，"
     "台账外数字显式标警——把“可信”从口号变成机制"),
    ("确定性评分 × 受控 LLM", "评分排名走纯代码（可复算），LLM 只做理解、编排与叙事；"
     "职责分离让“智能”与“可靠”兼得"),
    ("动态追问与案例研究员", "快捷问题按本次结果实时生成；AI 案例研究员自动发现"
     "相近品牌并对照我们的排名"),
]
x = 1.75
for t, d in inns:
    card(s, x, 1.9, 3.5, 3.3)
    add_text(s, x + 0.25, 2.2, 3.0, 0.5, [(t, True, PRIMARY, 15)])
    add_text(s, x + 0.25, 2.8, 3.05, 2.3, [(d, False, TEXT, 12.5)])
    x += 3.7
add_text(s, 1.75, 5.6, 11, 0.8,
         [("创新不是堆功能，而是把“AI 应用的最大短板——不可信”变成产品的核心机制。",
           True, NAVY, 14)])

# ================= 13 §四-2 独特视角 =================
s = light_slide("04", "创新性与独特视角 · 视角", 13, "面向中小卖家的“可验证智能体”")
add_text(s, 1.75, 1.7, 11, 0.5,
         [("不做“更大的模型”，做“更可信的流程”。", True, NAVY, 18)])
tri = [
    ("数据 → 解读 → 动作", "不只给数字，更解释数字对卖家的意义，并落到可执行的第一步"),
    ("跨学科交叉", "软件工程（管线与守卫）× 国际贸易实务（HS 编码与贸易数据）× "
     "数据科学（多准则评分）"),
    ("小即是美", "切口足够小（选市场），才能在 20 页内把深度、可信与体验同时做满"),
]
y = 2.5
for t, d in tri:
    add_text(s, 1.75, y, 3.6, 0.45, [(t, True, PRIMARY, 15)])
    add_text(s, 5.6, y, 7.1, 0.9, [(d, False, TEXT, 13)])
    y += 1.05
add_text(s, 1.75, 6.0, 11, 0.6,
         [("评委可以打开应用亲自验证：换权重、换品类、任意追问——结论随数据走，而不是随模型走。",
           False, TEXT, 13)])

# ================= 14 §五-1 结果解读 =================
s = light_slide("05", "结果解释与建议 · 解读", 14, "Top5 结果解读（便携咖啡机）")
t5 = DATA["ranking"][:5]
t_tbl = [["排名", "市场", "总分", "进口额(亿美元)", "中国份额", "年均增速"]]
for x in t5:
    t_tbl.append([str(x["rank"]), x["name"], "{:.3f}".format(x["total"]),
                  "{:.2f}".format(x["scale_yi"]), "{:.1f}%".format(x["china_share"]),
                  "{:.1f}%".format(x["growth"])])
tb = s.shapes.add_table(6, 6, Inches(1.75), Inches(1.6), Inches(10.9), Inches(2.7)).table
widths = [0.9, 1.6, 1.4, 2.6, 1.8, 1.6]
for c_i, wdt in enumerate(widths):
    tb.columns[c_i].width = Inches(wdt)
for r_i, row in enumerate(t_tbl):
    for c_i, cell_text in enumerate(row):
        cell = tb.cell(r_i, c_i)
        cell.text = cell_text
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                set_font(run, 12, r_i == 0 or c_i == 1,
                         RGBColor(0xFF, 0xFF, 0xFF) if r_i == 0 else TEXT)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r_i == 0 else (TINT if r_i % 2 else BG_LIGHT)
cd = CategoryChartData()
cd.categories = [x["name"] for x in t5]
cd.add_series("中国份额%", tuple(x["china_share"] for x in t5))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1.75), Inches(4.55),
                        Inches(10.9), Inches(2.1), cd)
chart = gf.chart
chart.has_title = False
chart.font.size = Pt(11)
chart.has_legend = False
plot = chart.plots[0]
plot.vary_by_categories = True
ser = plot.series[0]
ser.format.fill.solid()
ser.format.fill.fore_color.rgb = PRIMARY
pt = ser.points[0]
pt.format.fill.solid()
pt.format.fill.fore_color.rgb = ACCENT
va2 = chart.value_axis
va2.has_title = True
va2.axis_title.text_frame.text = "中国份额（%）"
for p_ in va2.axis_title.text_frame.paragraphs:
    for r_ in p_.runs:
        set_font(r_, 11, False, MUTED)
source_line(s, "数据来源：UN Comtrade HS 841981，检索 2026-10")

# ================= 15 §五-2 雷达与维度解读 =================
s = light_slide("05", "结果解释与建议 · 维度", 15, "六维画像：美国 vs 德国 vs 马来西亚")
cd = CategoryChartData()
dims = ["规模", "增速", "中国份额", "购买力", "数字渠道", "物流"]
cd.categories = dims
for nm in ("美国", "德国", "马来西亚"):
    sub = RANK[nm]["sub"]
    cd.add_series(nm, tuple(sub[k] for k in
                  ("scale", "growth", "china_affinity", "purchase_power", "digital", "logistics")))
gf = s.shapes.add_chart(XL_CHART_TYPE.RADAR, Inches(1.75), Inches(1.55),
                        Inches(6.4), Inches(4.9), cd)
chart = gf.chart
chart.has_title = False
chart.font.size = Pt(11)
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
add_text(s, 8.6, 1.8, 4.1, 4.6,
         [("三个形状，三种打法", True, PRIMARY, 15),
          ("美国：全维度均衡的高分六边形——综合实力型市场，拼产品与品牌",
           False, TEXT, 12.5),
          ("德国：增长与物流突出、规模中游——稳扎稳打的欧洲桥头堡",
           False, TEXT, 12.5),
          ("马来西亚：增速与中国份额双高、规模小——适合小预算快速试错的先发市场",
           False, TEXT, 12.5),
          (" ", False, TEXT, 8),
          ("雷达不是装饰：它解释了“为什么总分接近的两国，打法应当完全不同”。",
           False, MUTED, 12)])
source_line(s, "子项得分 0-10（候选池内归一化），数据截至 2023 年进口年度")

# ================= 16 §五-3 案例对照佐证 =================
s = light_slide("05", "结果解释与建议 · 案例佐证", 16, "真实品牌怎么走，我们就验证出什么")
cases = [
    ("石头科技 Roborock", "扫地机器人同品类：据年报，境外收入占比近五成，以美国、德国等欧美市场为主力。",
     "其主攻市场 USA、DEU 落在我们评分的第 1、2 名"),
    ("COSORI（Vesync）", "空气炸锅品类：深耕亚马逊美国站，长期位居品类线上销量前列。",
     "与我们「美国优先」的推荐路径一致"),
]
y = 1.7
for t, d, align_t in cases:
    card(s, 1.75, y, 10.9, 1.5)
    add_text(s, 2.0, y + 0.16, 10.4, 0.5, [(t, True, PRIMARY, 14.5)])
    add_text(s, 2.0, y + 0.62, 10.4, 0.75, [(d, False, TEXT, 12.5)])
    add_text(s, 2.0, y + 1.14, 10.4, 0.35, [(align_t + "（对照由代码自动计算）", True, ACCENT, 11.5)])
    y += 1.72
add_text(s, 1.75, 6.2, 11, 0.6,
         [("方法论自洽：真实品牌的成功路径，与数据推导的推荐方向相互印证——"
           "这不是巧合，而是同一套市场规律的不同投影。", True, NAVY, 13.5)])
source_line(s, "来源：公司年报及公开报道（检索 2026-10）；对照计算见代码 luopan/cases.py")

# ================= 17 §五-4 风险与应对 =================
s = light_slide("05", "结果解释与建议 · 风险", 17, "风险识别与应对")
risks = [
    ("中国份额是双刃剑", "接受度高同时意味着价格战激烈",
     "差异化定位（容量/设计/配套），避开纯比价"),
    ("增速平稳≠躺赢", "美国 6.7% 增速靠运营抢量，而非自然红利",
     "小预算 FBA 单 listing 先验证转化，再决定加投"),
    ("数据时效与缺失", "贸易数据年度更新，个别维度缺失",
     "缺失显式标注 + 年度自动更新 + 用户可复核原始数据"),
    ("品类映射错误", "AI 编码映射可能偏差",
     "三级识别 + 人工兜底输入，界面全程可见拆解过程"),
]
y = 1.7
for t, risk, resp in risks:
    card(s, 1.75, y, 10.9, 1.06)
    add_text(s, 2.0, y + 0.12, 3.4, 0.8, [(t, True, PRIMARY, 13.5)])
    add_text(s, 5.5, y + 0.12, 3.2, 0.8, [("风险：" + risk, False, TEXT, 11.5)])
    add_text(s, 8.9, y + 0.12, 3.6, 0.8, [("应对：" + resp, False, TEXT, 11.5)])
    y += 1.2
add_text(s, 1.75, 6.55, 11, 0.4,
         [("风险层的存在本身就是产品能力：能说清“什么时候不该信我”的系统，才值得被信任。",
           True, NAVY, 13)])

# ================= 18 §五-5 问题与优化路线 =================
s = light_slide("05", "结果解释与建议 · 优化", 18, "我们知道自己的边界，以及下一步")
opts = [
    ("定价与汇率维度", "当前价位仅作输入口径", "引入电商价格带数据与汇率敏感性分析"),
    ("实时竞品信号", "贸易数据为年度粒度", "接入电商榜单位移与社媒声量作为高频补充"),
    ("多语言输出", "报告目前为简体中文", "按目标市场语言生成本地化报告（德/日/西）"),
    ("治理数据源扩展", "WGI 监管质量指标暂缺", "接入世界银行 WGI 完善制度环境维度"),
]
y = 1.7
for t, now, nxt in opts:
    card(s, 1.75, y, 10.9, 1.02)
    add_text(s, 2.0, y + 0.12, 3.2, 0.75, [(t, True, PRIMARY, 13.5)])
    add_text(s, 5.3, y + 0.12, 3.2, 0.75, [("现状：" + now, False, TEXT, 11.5)])
    add_text(s, 8.7, y + 0.12, 3.8, 0.75, [("下一步：" + nxt, False, TEXT, 11.5)])
    y += 1.18
add_text(s, 1.75, 6.5, 11, 0.4,
         [("诚实的边界陈述是优化路线图的起点——每一条都有明确的实现路径。", True, NAVY, 13)])

# ================= 19 §六-1 应用界面 =================
from PIL import Image as PILImage

def crop_png(src, dst, top_r, bot_r):
    im = PILImage.open(src)
    w, h = im.size
    im.crop((0, int(h * top_r), w, int(h * bot_r))).save(dst)

crop_png(SHOT / "shot_results2.png", SHOT / "crop_results.png", 0.16, 1.0)
s = light_slide("06", "应用结果呈现 · 界面", 19, "智能体应用界面")
add_text(s, 1.75, 1.5, 11, 0.4,
         [("选择式输入（品类/价位/区域/权重）→ 一键分析 → 结果与依据同屏呈现。", False, TEXT, 13)])
img = PILImage.open(SHOT / "crop_results.png")
img_w = 8.5
img_h = img_w * img.size[1] / img.size[0]
s.shapes.add_picture(str(SHOT / "crop_results.png"), Inches(1.75), Inches(1.95),
                     width=Inches(img_w))
add_text(s, 1.75, 1.95 + img_h + 0.12, 8.5, 0.35,
         [("应用界面：价位与区域设置（上）→ 指标卡与排名表、Top10 图（下）", False, MUTED, 11)])
add_text(s, 10.55, 1.95, 2.2, 4.4,
         [("交互要点", True, PRIMARY, 13.5),
          ("选择式输入，小众品类走 AI 拆解且过程可见", False, TEXT, 11.5),
          ("六维权重的滑条实时重排", False, TEXT, 11.5),
          ("守卫警告显式展示", False, TEXT, 11.5),
          ("追问次数不限", False, TEXT, 11.5)])

# ================= 20 §六-2 提示词与链接（深蓝收尾） =================
s = dark_slide()
add_text(s, M + 0.2, 0.55, 12, 0.4, [("应用结果呈现 · 提示词示例与智能体链接", True, ACCENT, 14)])
add_text(s, M + 0.2, 1.0, 12, 0.6, [("三个提示词，看懂三种能力", True, RGBColor(0xFF, 0xFF, 0xFF), 24)])
prompts = [
    ("① 评分与依据", "“便携咖啡机，零售价300元，主攻线上渠道”",
     "六维加权评分 → Top5 排名与依据卡 → 守卫核验的通俗点评"),
    ("② 约束重排", "“如果只看东南亚还有哪些机会？”",
     "东南亚子池内重新归一化排序，马来西亚以增速+渠道双高居首"),
    ("③ 对比归因", "“第一名和第二名对比一下，选哪个？”",
     "双市场逐维度对比，数字全部来自台账，结论可直接执行"),
]
y = 1.9
for t, q, r in prompts:
    add_text(s, M + 0.2, y, 12, 0.4, [(t, True, ACCENT, 14)])
    add_text(s, M + 0.2, y + 0.38, 12, 0.4, [(q, False, RGBColor(0xFF, 0xFF, 0xFF), 13)])
    add_text(s, M + 0.2, y + 0.74, 12, 0.4, [(r, False, RGBColor(0xA9, 0xBA, 0xCC), 12)])
    y += 1.32
add_text(s, M + 0.2, 5.95, 12, 0.5,
         [("智能体访问链接与评审测试账号", True, RGBColor(0xFF, 0xFF, 0xFF), 15)])
add_text(s, M + 0.2, 6.4, 12, 0.5,
         [("随作品提交包提供（含访问码），评审期间持续在线；数据来源与全部代码见随附仓库。",
           False, RGBColor(0xA9, 0xBA, 0xCC), 12)])
add_text(s, M + 0.2, 7.0, 12, 0.4,
         [("出海罗盘 · 让每一次出海决策，都有据可依。", True, ACCENT, 14)])

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("saved:", OUT, "| slides:", len(prs.slides.__iter__.__self__._sldIdLst))
