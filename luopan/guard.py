"""数字台账守卫：LLM 叙事中的每个数字都必须来自台账，防幻觉（research-deck 打法）。"""
import math
import re

NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def extract_numbers(text):
    out = []
    for tok in NUM_RE.findall(text or ""):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            pass
    return out


def build_ledger(*items):
    """把台账来源（事实清单字符串、原始数值）里的所有数字收进集合。"""
    ledger = set()
    for it in items:
        if it is None:
            continue
        if isinstance(it, (int, float)):
            ledger.add(float(it))
        else:
            ledger.update(extract_numbers(str(it)))
    return ledger


def check(text, ledger, rel_tol=0.005):
    """返回不在台账中的数字列表。年份与 ≤30 的整数（排名/序数）豁免。"""
    bad = []
    for n in extract_numbers(text):
        if n == int(n) and 1900 <= n <= 2100:
            continue  # 年份
        if n == int(n) and 0 <= n <= 30:
            continue  # 排名/序数/小整数
        if not any(math.isclose(n, m, rel_tol=rel_tol) for m in ledger):
            bad.append(n)
    return bad
