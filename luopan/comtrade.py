"""UN Comtrade public preview 抓取（免密钥、匿名额度未公开）。

2026-10-12 实测约束：
- 每次调用只收 1 个 period，多年报错 "Maximum number of periods for preview is 1"
- 单次调用返回该 reporter 当年该 HS6 对全部伙伴国的分解（含 partnerCode=0 世界
  合计与 156 中国），无需为"自中国进口"单独调用
- 策略：限速 + 429/503 退避 + 全量缓存跨天续跑
"""
import time

import requests

from . import cache

API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
PAUSE_SEC = 1.1
BACKOFF_SEC = (5, 15, 45, 120)


def cache_key(reporter: int, hs6: str, year: int) -> str:
    return "cty_{}_{}_{}".format(reporter, hs6, year)


def fetch_year(reporter: int, hs6: str, year: int, offline: bool = False):
    """返回 (records, state)，state ∈ fresh/cache/missing。"""
    key = cache_key(reporter, hs6, year)
    hit = cache.get("comtrade", key)
    if hit is not None:
        return hit["data"], "cache"
    if offline:
        return [], "missing"
    params = {"reporterCode": reporter, "period": year, "cmdCode": hs6, "flowCode": "M"}
    resp = None
    for wait in (0,) + BACKOFF_SEC:
        if wait:
            time.sleep(wait)
        resp = requests.get(API, params=params, timeout=30)
        if resp.status_code in (429, 503):
            continue
        break
    if resp.status_code in (429, 503):
        raise RuntimeError("comtrade 限流未恢复: {}".format(params))
    resp.raise_for_status()
    rows = resp.json().get("data") or []
    records = [
        {
            "reporter": r.get("reporterCode"),
            "year": int(r["period"]),
            "hs6": hs6,
            "flow": r.get("flowCode"),
            "partner": r.get("partnerCode"),
            "value_usd": r.get("primaryValue"),
            "net_wgt": r.get("netWgt"),
        }
        for r in rows
    ]
    time.sleep(PAUSE_SEC)
    cache.put("comtrade", key, params, records)
    return records, "fresh"
