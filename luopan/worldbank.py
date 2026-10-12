"""World Bank API v2 抓取（免密钥，分号分隔多国批量）。

偶发返回单元素错误信封 [{"message":[...]}]（暂态），已做识别+重试。
"""
import time

import requests

from . import cache

API = "https://api.worldbank.org/v2"


def fetch_indicator(indicator: str, iso3_list, year_from: int, year_to: int, offline: bool = False):
    """返回 (records, state)，state ∈ fresh/cache/missing。records: [{iso3, indicator, year, value}]"""
    key = "wb_{}_{}-{}_{}".format(indicator, year_from, year_to, "-".join(sorted(iso3_list)))
    hit = cache.get("worldbank", key)
    if hit is not None:
        return hit["data"], "cache"
    if offline:
        return [], "missing"
    resp = None
    payload = None
    for attempt in range(6):
        resp = requests.get(
            "{}/country/{}/indicator/{}".format(API, ";".join(iso3_list), indicator),
            params={"format": "json", "date": "{}:{}".format(year_from, year_to), "per_page": 500},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        # 偶发返回错误信封 [{"message":[...]}]（误导性的 "120 Invalid value"，实为
        # 服务端暂态抖动）；正常响应是 [meta, rows] 两元素
        if isinstance(payload, list) and len(payload) == 2:
            break
        time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError("world bank 连续返回错误信封: {}".format(str(payload)[:200]))
    points = payload[1] or []
    records = [
        {"iso3": p["countryiso3code"], "indicator": indicator, "year": int(p["date"]), "value": p["value"]}
        for p in points
        if p.get("value") is not None
    ]
    cache.put("worldbank", key, {"indicator": indicator, "years": [year_from, year_to]}, records)
    return records, "fresh"
