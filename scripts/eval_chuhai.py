# -*- coding: utf-8 -*-
"""chuhai-eval-dataset 评测 harness（诚实评测，不针对答案调参）。

用法（在项目根目录）：
  python scripts/eval_chuhai.py --tier keyword          # 确定性识别层，全量 324
  python scripts/eval_chuhai.py --tier llm --n 30       # AI 拆解识别，分层抽样
  python scripts/eval_chuhai.py --tier edge             # 红线/管制合规筛查，全量 35
  python scripts/eval_chuhai.py --tier chain --n 3      # 评分全链路抽查

原则：本 harness 只测量当前代码行为。合规筛查层基于公开法规类目构建，
未记忆评测条目答案；评测结果用于发现缺口，不做逐条过拟合。
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVAL_DIR = ROOT.parent / "chuhai-eval-dataset" / "out"
DEFAULT_FALLBACK_QS = ["如果只看东南亚还有哪些机会？", "第一名和第二名对比一下，选哪个？",
                       "中国份额是什么意思？"]

_norm = lambda s: str(s).replace(" ", "").replace("　", "").lower()


def load():
    rows = [json.loads(l) for l in (EVAL_DIR / "test_inputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    edges = [json.loads(l) for l in (EVAL_DIR / "edge_case_inputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows, edges


def tier_keyword(rows):
    from luopan.profile import lookup_hs6
    hit = n = 0
    misses = []
    for r in rows:
        n += 1
        want = r["expect"].get("hs6")
        got = None
        try:
            got = lookup_hs6(r["query"])
        except Exception:
            pass
        if got and got == want:
            hit += 1
        else:
            misses.append(r["id"])
    return {"tier": "keyword(确定性)", "n": n, "hs6_exact": hit,
            "rate": round(hit / n * 100, 1), "miss_sample": misses[:10]}


def tier_llm(rows, n=30, seed=42):
    from luopan.profile import smart_build_profile
    from luopan.config import CATEGORY_TREE
    random.seed(seed)
    sample = random.sample(rows, min(n, len(rows)))
    hs2major = {}
    for major, subs in CATEGORY_TREE.items():
        for x in subs:
            hs2major.setdefault(x["hs6"], major)
    exact = heading = l1_match = tree_out = err = 0
    details = []
    t0 = time.time()
    for i, r in enumerate(sample, 1):
        exp = r["expect"]
        try:
            prof, info = smart_build_profile(r["query"])
        except Exception as e:
            err += 1
            details.append({"id": r["id"], "error": str(e)[:80]})
            continue
        got = prof.hs6 if prof else None
        rec = {"id": r["id"], "want": exp.get("hs6"), "got": got,
               "matched_by": info.get("matched_by")}
        if got:
            if got == exp.get("hs6"):
                exact += 1
            elif got[:4] == (exp.get("hs6") or "")[:4]:
                heading += 1
            if hs2major.get(got) == exp["l1"]:
                l1_match += 1
            elif exp["l1"] not in CATEGORY_TREE:
                tree_out += 1  # 池外大类：AI 映射到最近编码属正确行为
        details.append(rec)
        print("  [{}/{}] {} want={} got={} {}s".format(
            i, len(sample), r["id"], exp.get("hs6"), got,
            round(time.time() - t0)), flush=True)
    return {"tier": "llm-split(抽样)", "n": len(sample), "hs6_exact": exact,
            "heading4_only": heading, "l1_in_tree_match": l1_match,
            "tree_out_ok": tree_out, "errors": err,
            "seconds": round(time.time() - t0), "details": details}


def tier_edge(edges):
    from luopan.compliance import screen_product
    res = {"红线禁售": {"total": 0, "refuse": 0},
           "高合规管制": {"total": 0, "degrade": 0, "refuse": 0, "none": 0},
           "出口管制": {"total": 0, "degrade": 0, "refuse": 0, "none": 0},
           "运输管制": {"total": 0, "degrade": 0, "none": 0},
           "文化敏感": {"total": 0, "note": 0, "none": 0}}
    cover_hits = cover_total = 0
    misses = []
    for e in edges:
        risk = e["risk"]
        comp = screen_product(e["query"])
        bucket = res.setdefault(risk, {"total": 0})
        bucket["total"] += 1
        sev = comp["severity"]
        key = sev if sev in bucket else ("none" if sev is None else "other")
        bucket[key] = bucket.get(key, 0) + 1
        msg = _norm(json.dumps(comp["message"], ensure_ascii=False))
        for kw in e["expect"].get("must_cover", []):
            cover_total += 1
            if _norm(kw) in msg:
                cover_hits += 1
            else:
                misses.append("{}: {}".format(e["id"], kw))
    return {"tier": "edge(合规筛查)", "by_risk": res,
            "must_cover_召回": "{}/{}".format(cover_hits, cover_total),
            "召回率": round(cover_hits / cover_total * 100, 1) if cover_total else None,
            "未召回关键词样例": misses[:12]}


def tier_chain(rows, n=3, seed=7):
    """全链路抽查：识别→(必要时补数)→评分→守卫叙事，验证评分链路不被合规层破坏。"""
    from luopan.agent import MarketAgent
    random.seed(seed)
    cached = [r for r in rows if r["expect"].get("hs6") in
              ("841981", "851671", "850811", "852862", "850980", "950300")]
    sample = random.sample(cached, min(n, len(cached)))
    out = []
    agent = MarketAgent()
    for r in sample:
        try:
            res = agent.run(r["query"])
            out.append({"id": r["id"], "hs6": r["expect"]["hs6"],
                        "ranked": bool(res.ranking), "error": res.error,
                        "top1": res.ranking[0]["name"] if res.ranking else None})
        except Exception as e:
            out.append({"id": r["id"], "error": str(e)[:80]})
    return {"tier": "chain(全链路抽查)", "cases": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True,
                    choices=["keyword", "llm", "edge", "chain"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rows, edges = load()
    if args.tier == "keyword":
        report = tier_keyword(rows)
    elif args.tier == "llm":
        report = tier_llm(rows, n=args.n, seed=args.seed)
    elif args.tier == "edge":
        report = tier_edge(edges)
    else:
        report = tier_chain(rows, n=args.n, seed=args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    out = EVAL_DIR / "eval_report_last.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    print("报告已写:", out)


if __name__ == "__main__":
    main()
