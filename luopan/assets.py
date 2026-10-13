"""UI 资产：手绘 SVG 图标库与样式生成器（零外部依赖，矢量任意缩放）。

设计语言：深海蓝 #0B3D66 × 罗盘金 #F59E0B，线性图标 1.8px 圆头描边。
"""

NAVY = "#0B3D66"
BLUE = "#1B6CB0"
GOLD = "#F59E0B"
INK = "#1F2937"

# 每个大类的图标（24×24 viewBox 线性路径）
CATEGORY_ICONS = {
    "厨房与家居电器": '<path d="M4 11h16M6 11v5a4 4 0 004 4h4a4 4 0 004-4v-5M2.5 11h1.5m16 0h1.5M9 3.5L11 6m6-2.5L15 6"/>',
    "家居与照明": '<path d="M8 3.5h8l3 6.5H5l3-6.5zM12 10v6M9 20h6M12 16v4"/>',
    "餐厨与五金": '<path d="M7 3v7m3-7v7m-3 0a3 3 0 006 0m-3 3v11M16 3c-1.5 1-2.5 3-2.5 5.5 0 2 1 3 2.5 3V21m0-18v5.5"/>',
    "消费电子": '<rect x="6.5" y="2.5" width="11" height="19" rx="2.5"/><path d="M10 5h4M12 18.5h.01"/>',
    "智能宠物": '<circle cx="7" cy="8" r="2"/><circle cx="12" cy="5.5" r="2"/><circle cx="17" cy="8" r="2"/><path d="M12 10.5c-2.8 0-5 2.2-5 4.7 0 1.6 1.2 2.8 2.8 2.8.8 0 1.5-.3 2.2-.3s1.4.3 2.2.3c1.6 0 2.8-1.2 2.8-2.8 0-2.5-2.2-4.7-5-4.7z"/>',
    "户外与出行": '<path d="M2.5 19L9 7l4 7m-3.5 5L14 11l7.5 8M2.5 19h19M16.5 5.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>',
    "健身与运动": '<path d="M6.5 6.5v11m11-11v11M3.5 9v6m17-6v6M6.5 12h11M2 12h1.5m17 0H22"/>',
    "美容与健康": '<path d="M12 3.5s6 6.5 6 11a6 6 0 01-12 0c0-4.5 6-11 6-11zM8.5 14.5a3.5 3.5 0 003.5 3.5"/>',
    "服饰与配件": '<path d="M9 3.5L5 6l-2 4.5 3.5 1.5V20h11v-8L21 10.5 19 6l-4-2.5a3 3 0 01-6 0z"/>',
    "玩具·游戏·母婴": '<rect x="3" y="8" width="8" height="8" rx="1.5"/><rect x="13" y="8" width="8" height="8" rx="1.5"/><path d="M7 11v2m-1-1h2m10-1.5h3m-1.5-1.5v3M11 12h2"/>',
    "食品与滋补": '<path d="M5 4h14l-1.5 8a5.5 5.5 0 01-11 0L5 4zM12 12v8m-4 0h8M9 7.5c0 2 1.5 3.5 3 4"/>',
    "汽车与车载": '<path d="M4 16v2.5M20 16v2.5M3 16l1.5-5.5A2 2 0 016.4 9h11.2a2 2 0 011.9 1.5L21 16H3zm2 0h14a1.5 1.5 0 100-3H5a1.5 1.5 0 100 3z"/>',
    "摄影与暗房": '<rect x="3" y="6.5" width="18" height="13" rx="2.5"/><path d="M8.5 6.5L10 4h4l1.5 2.5"/><circle cx="12" cy="13" r="3.5"/>',
}

# 功能区图标
SECTION_ICONS = {
    "input": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5L10 10l-1.5 5.5L14 13.5l1.5-5z"/>',
    "rank": '<path d="M4 20V10m5.5 10V4M15 20v-7m5.5 7V8M2.5 20h19"/>',
    "radar": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/><path d="M12 3v5m9 4h-5m-9 4l3.5-3.5"/>',
    "evidence": '<circle cx="11" cy="11" r="7"/><path d="M16.5 16.5L21 21M8.5 11h5m-5-3h5m-5 6h2.5"/>',
    "case": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5.5A1.5 1.5 0 0110.5 4h3A1.5 1.5 0 0115 5.5V7M3 12h18m-9 0v3"/>',
    "comment": '<path d="M4 5.5h16v10H12l-4.5 4v-4H4v-10z"/><path d="M8 9h8m-8 3h5"/>',
    "chat": '<path d="M20 11.5a8 8 0 10-3.5 6.6L21 19l-1-4.2c.6-1 .9-2.1.9-3.3z"/><path d="M8.5 10.5h7m-7 3h4"/>',
    "trace": '<path d="M4 19c4-1 3-6 7-7s5-5 4-8m2 15c-2 0-4-1-4-3"/><circle cx="17" cy="4" r="1.8"/><circle cx="13" cy="19" r="1.8"/>',
    "method": '<path d="M12 6c-2-1.8-5-2-8-1v14c3-1 6-.8 8 1 2-1.8 5-2 8-1V5c-3-1-6-.8-8 1zm0 0v14"/>',
    "star": '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8L3.5 9.7l5.9-.8L12 3.5z"/>',
    "shield": '<path d="M12 3l7.5 3v6c0 4.5-3 8-7.5 9.5C7.5 20 4.5 16.5 4.5 12V6L12 3z"/><path d="M9 11.5l2.2 2.2L15.5 9.5"/>',
    "price": '<path d="M12 3v18M8 7.5c0-1.5 1.8-2.5 4-2.5s4 1 4 2.5-1.5 2.2-4 2.8-4 1.2-4 2.7 1.8 2.5 4 2.5 4-1 4-2.5"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z"/>',
}


def icon(name, size=22, color=BLUE, stroke=1.8):
    """线性图标 → 内联 SVG HTML。name ∈ CATEGORY_ICONS ∪ SECTION_ICONS。"""
    path = (CATEGORY_ICONS.get(name) or SECTION_ICONS.get(name))
    if path is None:
        return ""
    return (
        '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="{w}" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-{va}px">{p}</svg>'
    ).format(s=size, c=color, w=stroke, va=size // 8, p=path)


def logo(size=46):
    """罗盘 Logo：深海蓝表盘 + 金色罗盘针。"""
    return (
        '<svg width="{s}" height="{s}" viewBox="0 0 48 48">'
        '<circle cx="24" cy="24" r="22" fill="{navy}"/>'
        '<circle cx="24" cy="24" r="17.5" fill="none" stroke="{gold}" stroke-width="1.6"/>'
        '<circle cx="24" cy="24" r="13" fill="none" stroke="{gold}" stroke-width="0.7" opacity="0.55"/>'
        '<path d="M31.5 16.5L26.8 26.8 16.5 31.5l4.7-10.3 10.3-4.7z" fill="{gold}"/>'
        '<circle cx="24" cy="24" r="2.3" fill="#fff"/>'
        '<path d="M24 2v3.5M24 42.5V46M2 24h3.5M42.5 24H46" stroke="{gold}" stroke-width="1.4"/>'
        '</svg>'
    ).format(s=size, navy=NAVY, gold=GOLD)


def _icon_html(name, size, color, bg):
    return ('<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:{b}px;height:{b}px;border-radius:9px;background:{bg};flex:none">{svg}</span>'
            ).format(b=size + 14, bg=bg,
                     svg=icon(name, size, color))


def header_html(icon_name, title, sub="", accent=BLUE, bg="#E8F0FB"):
    """分区标题：圆底图标 + 标题 + 副说明。"""
    sub_html = '<div style="color:#5B6B7C;font-size:0.88rem;margin-top:2px">{}</div>'.format(sub) if sub else ""
    return (
        '<div style="display:flex;align-items:center;gap:10px;margin:18px 0 6px">{ico}'
        '<div><div style="font-weight:700;font-size:1.05rem;color:{ink}">{t}</div>{sub}</div></div>'
    ).format(ico=_icon_html(icon_name, 20, accent, bg), ink=INK, t=title, sub=sub_html)


def banner_html(icon_name, title, sub, accent=GOLD, bg="#FFF6E5"):
    """选中品类横幅：金底图标 + 名称 + 说明。"""
    return (
        '<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;'
        'border:1px solid #F2E3C4;border-radius:12px;background:linear-gradient(90deg,#FFFBF2,#FFF6E5)">{ico}'
        '<div><div style="font-weight:700;color:{ink}">{t}</div>'
        '<div style="color:#8A6D1F;font-size:0.85rem">{sub}</div></div></div>'
    ).format(ico=_icon_html(icon_name, 22, "#8A6D1F", bg), ink=INK, t=title, sub=sub)


def hero_html():
    """品牌头图：Logo + 标题 + 副标语 + 三个数据徽章。"""
    badges = "".join(
        '<span style="display:inline-flex;align-items:center;gap:6px;background:#E8F0FB;'
        'border-radius:999px;padding:4px 12px;font-size:0.82rem;color:{navy}">{i}{t}</span>'.format(
            navy=NAVY, i=icon(n, 15, BLUE), t=t)
        for n, t in [("globe", "21 个候选市场"), ("rank", "6 维加权评分"),
                     ("shield", "数字台账核验"), ("globe", "世界银行 · UN Comtrade")])
    return (
        '<div style="display:flex;align-items:center;gap:16px;padding:4px 0 10px">{logo}'
        '<div style="flex:1"><div style="font-size:1.75rem;font-weight:800;color:{navy};'
        'letter-spacing:0.5px;line-height:1.15">出海罗盘 <span style="font-size:0.95rem;'
        'color:#8A94A6;font-weight:500">GlobalCompass</span></div>'
        '<div style="color:#5B6B7C;margin-top:4px">三步选出出海目标市场：'
        '<b style="color:{gold}">选品类 → 调偏好 → 看依据</b>，'
        '每一步都有公开数据支撑、可溯源、可复算。</div>'
        '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">{badges}</div>'
        '</div></div>'
    ).format(logo=logo(60), navy=NAVY, gold=GOLD, badges=badges)


GLOBAL_CSS = """
<style>
.block-container {padding-top: 1.4rem; max-width: 1180px;}
#MainMenu, footer {visibility: hidden;}
h1, h2, h3 {letter-spacing: 0.2px;}
.stButton > button {
    border-radius: 10px; font-weight: 600;
    transition: transform .05s ease, box-shadow .15s ease;
}
.stButton > button:hover {box-shadow: 0 2px 10px rgba(11,61,102,.15);}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1B6CB0, #0B3D66); border: none; color: #fff;
}
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #E5EAF2; border-radius: 14px;
    padding: 14px 16px; box-shadow: 0 1px 4px rgba(15,35,60,.05);
}
[data-testid="stMetricValue"] {color: #0B3D66;}
[data-testid="stExpander"] {
    border: 1px solid #E5EAF2; border-radius: 12px; background: #fff;
}
[data-testid="stDataFrame"] {border-radius: 10px;}
.stChatMessage {border-radius: 12px;}
hr {margin: 0.6rem 0;}
</style>
"""


def inject_shell():
    """在 Streamlit 里注入全局 CSS + 品牌头图（app 顶部调用一次）。"""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(hero_html(), unsafe_allow_html=True)


def section_header(st, icon_name, title, sub=""):
    st.markdown(header_html(icon_name, title, sub), unsafe_allow_html=True)
