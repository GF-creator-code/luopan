"""一条命令刷新全部数据：python -m luopan.refresh [--offline] [--cty-budget N]

- 默认：World Bank 全量（6 指标一次批量）+ Comtrade 按当日预算续跑
- --offline：只读缓存并重写 fixtures，不发任何网络请求（断网验收用）
- --cty-budget：本次 Comtrade 新调用数上限，配额未知，默认 80/天
"""
import argparse
import json
import time

from . import cache, comtrade, config, worldbank


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只读缓存汇总，不发网络请求")
    ap.add_argument("--cty-budget", type=int, default=80, help="本次 Comtrade 新调用数上限")
    args = ap.parse_args()

    iso3_all = sorted(config.COUNTRIES)
    wb_records = []
    wb_states = {}
    for ind, label in config.WB_INDICATORS.items():
        records, state = worldbank.fetch_indicator(ind, iso3_all, *config.WB_YEARS, offline=args.offline)
        wb_states[state] = wb_states.get(state, 0) + 1
        wb_records.extend(records)
        print("[{}] {} {} {}行".format(ind, label, state, len(records)))

    cty_records = []
    counts = {"fresh": 0, "cache": 0, "skip": 0}
    budget = args.cty_budget
    for hs6, meta in config.HS_PRESETS.items():
        hs_counts = {"fresh": 0, "cache": 0, "skip": 0}
        for iso3, info in config.COUNTRIES.items():
            if iso3 == "CHN":
                continue  # 中国是供给端参照，不是评分目标市场
            for year in meta["years"]:
                need_net = cache.get("comtrade", comtrade.cache_key(info["cty"], hs6, year)) is None
                if need_net and (args.offline or budget <= 0):
                    hs_counts["skip"] += 1
                    continue
                if need_net:
                    budget -= 1
                records, state = comtrade.fetch_year(info["cty"], hs6, year, offline=args.offline)
                hs_counts[state] = hs_counts.get(state, 0) + 1
                cty_records.extend(records)
        for k in counts:
            counts[k] += hs_counts[k]
        print("[{}] {} 新拉{} 缓存{} 跳过{}".format(hs6, meta["name_zh"], hs_counts["fresh"], hs_counts["cache"], hs_counts["skip"]))

    config.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    (config.FIXTURES_DIR / "worldbank.json").write_text(
        json.dumps({"updated_at": now, "records": wb_records}, ensure_ascii=False), encoding="utf-8")
    (config.FIXTURES_DIR / "comtrade.json").write_text(
        json.dumps({"updated_at": now, "records": cty_records}, ensure_ascii=False), encoding="utf-8")

    years_seen = sorted({r["year"] for r in cty_records})
    partners = sorted({r["partner"] for r in cty_records})
    print("---")
    print("World Bank: {} (fresh={} cache={} missing={})".format(
        len(wb_records), wb_states.get("fresh", 0), wb_states.get("cache", 0), wb_states.get("missing", 0)))
    print("Comtrade: 调用 新拉{} 缓存{} 跳过{}（剩余预算 {}）".format(counts["fresh"], counts["cache"], counts["skip"], budget))
    print("Comtrade 记录 {} 条，年份 {}，含 partner(0=世界,156=中国): {}".format(len(cty_records), years_seen, partners))
    print("fixtures → {}".format(config.FIXTURES_DIR))


if __name__ == "__main__":
    main()
