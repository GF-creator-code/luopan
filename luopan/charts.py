"""图表：Top 市场六维雷达小倍数图（UI 与作品 PPT 复用）。

雷达标签用英文：云端容器通常没有中文字体，中文会渲染成方块；
中文说明放在 Streamlit 的 markdown 层，不进 matplotlib。
"""
import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib import pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei",
                                   "Noto Sans CJK SC", "WenQuanYi Micro Hei",
                                   "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

_DIM_KEYS = ("scale", "growth", "china_affinity",
             "purchase_power", "digital", "logistics")
_DIM_LABELS = ("Scale", "Growth", "China\nShare",
               "Purchasing\nPower", "Digital", "Logistics")
_ACCENT = "#2563EB"


def radar_small_multiples(ranked, top_n=5):
    """每市场一张小雷达（六维 0-10 子分），返回 matplotlib Figure。"""
    top = ranked[:top_n]
    fig, axes = plt.subplots(1, len(top), figsize=(2.9 * len(top), 3.5),
                             subplot_kw=dict(polar=True))
    if len(top) == 1:
        axes = [axes]
    angles = np.linspace(0, 2 * np.pi, len(_DIM_KEYS), endpoint=False).tolist()
    angles += angles[:1]
    for ax, r in zip(np.atleast_1d(axes), top):
        vals = [max(0.0, r["sub"][k]) for k in _DIM_KEYS]
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=1.8, color=_ACCENT)
        ax.fill(angles, vals, alpha=0.18, color=_ACCENT)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(_DIM_LABELS, fontsize=7.5)
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels([])
        ax.set_title("#{} {}".format(r["rank"], r["iso3"]),
                     fontsize=10, fontweight="bold", color="#1F2937", pad=12)
    fig.tight_layout()
    return fig
