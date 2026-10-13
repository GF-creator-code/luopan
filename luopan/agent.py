"""出海罗盘 Agent：计划 → 品类定位 → 数据覆盖检查 → 六维评分 → 台账约束叙事。

分工红线：LLM 只负责计划措辞、校对表未命中的品类映射、给定数字下的叙事与追问
回答；评分/重排/对比全部走确定性代码（scoring.py）。叙事中的数字由 guard.py
对照台账核验（台账=事实清单+用户原文），防幻觉——直接回应章程"可验证智能体交互能力"。
"""
import json
import re
from dataclasses import asdict, dataclass, field

from .config import CACHE_DIR, COUNTRIES, FIXTURES_DIR, NAME_TO_ISO3, REGIONS
from .guard import build_ledger, check as guard_check
from .llm import LlmClient
from .profile import build_profile
from .scoring import Weights, build_features, score_markets

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
RANK_REF_RE = re.compile(r"第([一二三四五六七八九十\d]+)名")

INDICATOR_HELP = {
    "中国份额": "该市场此品类的进口中来自中国的占比：越高说明当地渠道对中国货接受度越好，但竞争通常也越激烈。",
    "LPI": "世界银行物流绩效指数（1-5 分），衡量清关效率、贸易基建与物流服务质量，越高越利于跨境履约。",
    "物流": "物流就绪维度采用世界银行 LPI（1-5 分），覆盖清关、基建、国际运输便利性等。",
    "互联网": "互联网渗透率（%），反映电商与线上营销渠道的基础覆盖。",
    "人均GDP": "人均 GDP（美元），衡量购买力；高价定位产品权重可上调。",
    "增速": "进口额首末年复合年均增速（CAGR），反映品类需求的扩张速度。",
    "关税": "评分未纳入关税；报告风险层引用世界银行制成品实施关税均值做提示， precise 税率需按目的国税则查询。",
}

SYSTEM_ANALYST = ("你是出海市场分析师。直接输出点评正文，第一句就是结论；不要展示思考或分析过程，"
                  "不要解释你将做什么。只允许使用用户材料中出现过的数字，禁止编造、推算或"
                  "引入材料外数字（包括对材料数字做加减乘除得到的新数字）。语言简洁。")


def _merged_cty_records():
    """fixtures 为主体，叠加本地缓存里后续抓取的记录（云端按需抓取场景）。"""
    base = json.loads((FIXTURES_DIR / "comtrade.json").read_text(encoding="utf-8"))["records"]
    seen = {(r.get("hs6"), r.get("reporter"), r.get("year"), r.get("partner")) for r in base}
    cache_dir = CACHE_DIR / "comtrade"
    if cache_dir.exists():
        for p in sorted(cache_dir.glob("cty_*.json")):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for r in payload.get("data") or []:
                k = (r.get("hs6"), r.get("reporter"), r.get("year"), r.get("partner"))
                if k not in seen:
                    seen.add(k)
                    base.append(r)
    return base


def _load_fixtures():
    wb = json.loads((FIXTURES_DIR / "worldbank.json").read_text(encoding="utf-8"))["records"]
    return wb, _merged_cty_records()


def _factsheet(ranked, top_n=5):
    """给 LLM 的事实清单（它只许从这里抄数字），同时作为守卫台账来源。"""
    lines = []
    for r in ranked[:top_n]:
        raw = r["raw"]
        lines.append(
            "{}. {}（{}）：总分{}；{}年自全球进口{:.2f}亿美元；中国份额{:.1f}%；进口额年均增速{:.1f}%；人均GDP{:.0f}美元".format(
                r["rank"], r["name_zh"], r["iso3"], r["total"], raw["scale_year"],
                (raw["scale"] or 0) / 1e8,
                (raw["china_share"] or 0) * 100,
                (raw["growth"] or 0) * 100,
                raw["purchase_power"] or 0))
    return "\n".join(lines)


def _weights_dict(w):
    return {"规模": w.scale, "增速": w.growth, "中国份额": w.china_affinity,
            "购买力": w.purchase_power, "数字渠道": w.digital, "物流": w.logistics}


@dataclass
class AgentResult:
    text: str
    profile: object
    weights: Weights
    ranking: object
    trace: list
    summary: str = None
    guard_warnings: list = field(default_factory=list)
    narrative_error: str = None
    error: str = None

    def to_json(self):
        return {
            "profile": asdict(self.profile) if self.profile else None,
            "weights": _weights_dict(self.weights),
            "ranking": self.ranking,
            "trace": self.trace,
            "summary": self.summary,
            "guard_warnings": self.guard_warnings,
            "narrative_error": self.narrative_error,
            "error": self.error,
        }


class MarketAgent:
    def __init__(self, llm=None, wb_records=None, cty_records=None):
        self.llm = llm  # 可注入测试假 client；None 时首次用到才加载真 client
        self._wb = wb_records
        self._cty = cty_records

    def _ensure_llm(self):
        if self.llm is None:
            self.llm = LlmClient()
        return self.llm

    def _ensure_data(self):
        if self._wb is None:
            self._wb, self._cty = _load_fixtures()
        return self._wb, self._cty

    def coverage(self, hs6):
        """该品类在本地数据中的覆盖情况：(有进口数据的市场数, 年份列表)。"""
        _, cty = self._ensure_data()
        rows = [r for r in cty if r.get("hs6") == hs6]
        n = len({r.get("reporter") for r in rows if r.get("partner") == 0})
        return n, sorted({r.get("year") for r in rows})

    def run(self, text, weights=None, top_n=5, on_step=None, region_iso3s=None,
            profile=None):
        trace = []

        def step(action, detail, observation):
            trace.append({"step": len(trace) + 1, "action": action,
                          "detail": detail, "observation": observation})
            if on_step:
                on_step(trace[-1])

        w = weights or Weights()
        wb, cty = self._ensure_data()

        # 1 计划
        plan = "解析产品→映射HS编码→核对数据覆盖→六维加权评分→输出Top{}与叙事".format(top_n)
        try:
            plan = self._ensure_llm().chat([
                {"role": "system", "content": "你是出海市场调研Agent。用一句话（不超过40字）说明你将如何为目标产品筛选出海目标市场，直接输出这句话。"},
                {"role": "user", "content": text},
            ], max_tokens=100).strip().splitlines()[0][:80]
        except Exception as e:
            step("plan", text, "LLM 计划失败，改用默认计划: {}".format(e))
        step("plan", text, plan)

        # 2 品类定位（profile 由界面/调用方传入时直接采用，不再从文字重推）
        if profile is not None:
            prof = profile
            step("map_hs_code", text, "界面已选定 HS{}（{}）".format(prof.hs6, prof.matched_by))
        else:
            prof = build_profile(text, use_llm=True)
            if prof is None:
                step("map_hs_code", text, "校对表与 LLM 均未能确定 HS6，需要用户手选")
                return AgentResult(text, None, w, None, trace,
                                   error="无法确定品类，请手选 6 位 HS 编码")
            step("map_hs_code", text, "{} → {}（{}，{}）".format(
                text, prof.hs6, prof.hs_name_zh or "自定义品类", prof.matched_by))

        # 3 数据覆盖
        rows = [r for r in cty if r.get("hs6") == prof.hs6]
        if not rows:
            step("check_data", "hs6={}".format(prof.hs6), "本地缓存无该品类数据")
            return AgentResult(text, prof, w, None, trace,
                               error="本地缓存没有该品类数据，请先运行 python -m luopan.refresh")
        n_market = len({r.get("reporter") for r in rows if r.get("partner") == 0})
        years = sorted({r.get("year") for r in rows})
        step("check_data", "hs6={}".format(prof.hs6),
             "{} 个市场有进口数据，年份 {}".format(n_market, years))

        # 4 评分（可选区域过滤：子池内重新归一化）
        feats = build_features(prof.hs6, wb, cty)
        if region_iso3s:
            feats = {k: v for k, v in feats.items() if k in set(region_iso3s)}
            if not feats:
                return AgentResult(text, prof, w, [], trace,
                                   error="所选区域内没有候选市场数据")
        ranked = score_markets(feats, w)
        step("score_markets", "权重 {}".format(_weights_dict(w)) +
             ("，区域子池 {} 市场".format(len(feats)) if region_iso3s else ""),
             "{} 个市场排序完成，Top1 {}".format(len(ranked), ranked[0]["name_zh"]))

        # 5 叙事（台账约束 + 守卫核验）
        summary, guard_bad, narrative_error = None, [], None
        try:
            facts = _factsheet(ranked, top_n)
            answer = self._ensure_llm().chat([
                {"role": "system", "content": SYSTEM_ANALYST},
                {"role": "user", "content": "产品：{}\nHS编码：{}\n评分结果（默认权重）:\n{}\n请用3-4句点评Top{}格局，并点名最有潜力的1个市场及理由。".format(
                    text, prof.hs6, facts, min(top_n, len(ranked)))},
            ], max_tokens=800).strip()
            guard_bad = guard_check(answer, build_ledger(facts, text, prof.hs6, *(r["total"] for r in ranked)))
            summary = answer
            step("narrative", facts,
                 answer + ("" if not guard_bad else "\n[守卫警告] 台账外数字: {}".format(guard_bad)))
        except Exception as e:
            narrative_error = str(e)
            step("narrative", "-", "LLM 叙事失败（评分结果不受影响）: {}".format(e))

        return AgentResult(text, prof, w, ranked, trace, summary=summary,
                           guard_warnings=guard_bad, narrative_error=narrative_error)

    def regen_summary(self, result):
        """重试生成分析师点评（不重跑评分）；返回 (ok, 错误信息|None)。"""
        try:
            self._ensure_llm()
        except Exception as e:
            return False, str(e)
        self._ensure_data()
        facts = _factsheet(result.ranking, top_n=min(5, len(result.ranking)))
        try:
            answer = self._ensure_llm().chat([
                {"role": "system", "content": SYSTEM_ANALYST},
                {"role": "user", "content": "产品：{}\nHS编码：{}\n评分结果:\n{}\n请用3-4句点评Top格局，并点名最有潜力的1个市场及理由。".format(
                    result.text, result.profile.hs6, facts)},
            ], max_tokens=800).strip()
        except Exception as e:
            return False, str(e)
        result.summary = answer
        result.guard_warnings = guard_check(
            answer, build_ledger(facts, result.text, result.profile.hs6,
                                 *(r["total"] for r in result.ranking)))
        result.narrative_error = None
        result.trace.append({"step": len(result.trace) + 1, "action": "narrative_retry",
                             "detail": facts, "observation": answer})
        return True, None

    def followup(self, question, result):
        """追问：区域重排 / 两国对比 / 指标解释 / 台账约束自由问答。"""
        trace = []

        def step(action, detail, observation):
            trace.append({"step": len(trace) + 1, "action": action,
                          "detail": detail, "observation": observation})

        wb, cty = self._ensure_data()
        q = (question or "").strip()

        # 排名称谓解析："第一名/第2名" → 排名表对应市场名
        rank_names = []
        for m in RANK_REF_RE.finditer(q):
            tok = m.group(1)
            n = int(tok) if tok.isdigit() else CN_NUM.get(tok)
            if n and 1 <= n <= len(result.ranking):
                rank_names.append(result.ranking[n - 1]["name_zh"])

        # 1) 区域重排：区域内重新归一化排序（子池内 min-max，名次变化是特性）
        region = next((r for r in REGIONS if r in q), None)
        if region:
            feats = {k: v for k, v in build_features(result.profile.hs6, wb, cty).items()
                     if k in set(REGIONS[region])}
            sub = score_markets(feats, result.weights)
            facts = _factsheet(sub, top_n=len(sub))
            answer, bad = None, []
            try:
                answer = self._ensure_llm().chat([
                    {"role": "system", "content": SYSTEM_ANALYST},
                    {"role": "user", "content": "产品：{}\n仅看{}市场的评分（子池内重新归一化）:\n{}\n用2-3句点评。".format(
                        result.text, region, facts)},
                ], max_tokens=500).strip()
                bad = guard_check(answer, build_ledger(facts, result.text, *(r["total"] for r in sub)))
            except Exception as e:
                answer = "（LLM 点评失败: {}）".format(e)
            step("rerank_region", "区域={}，{}个市场".format(region, len(sub)),
                 "子池 Top1 {}".format(sub[0]["name_zh"]))
            return {"kind": "rerank_region", "region": region, "ranking": sub,
                    "answer": answer, "guard": bad, "trace": trace}

        # 2) 两国对比（含"第一名/第二名"这类排名称谓）
        mentioned = [name for name in NAME_TO_ISO3 if name in q]
        for name in rank_names:
            if name not in mentioned:
                mentioned.append(name)
        if len(mentioned) >= 2 and any(k in q for k in ("对比", "比较", "哪个", "还是", "和", "选")):
            rows = [r for r in result.ranking if r["name_zh"] in mentioned[:2]]
            facts = _factsheet(sorted(rows, key=lambda r: r["rank"]), top_n=2)
            answer, bad = None, []
            try:
                answer = self._ensure_llm().chat([
                    {"role": "system", "content": SYSTEM_ANALYST},
                    {"role": "user", "content": "对比这两个市场，给出选择建议：\n{}\n注意：子项分数含义=规模/增速/中国份额/购买力/数字渠道/物流。".format(facts)},
                ], max_tokens=500).strip()
                bad = guard_check(answer, build_ledger(facts, result.text))
            except Exception as e:
                answer = "（LLM 对比失败: {}）".format(e)
            step("compare", "、".join(mentioned[:2]), "总排名 " + "、".join(
                "{}第{}名".format(r["name_zh"], r["rank"]) for r in rows))
            return {"kind": "compare", "rows": rows, "answer": answer, "guard": bad, "trace": trace}

        # 3) 指标解释（静态词典，零幻觉面，不需要 LLM）
        for key, help_text in INDICATOR_HELP.items():
            if key in q:
                step("explain", key, help_text)
                return {"kind": "explain", "answer": help_text, "guard": [], "trace": trace}

        # 4) 自由问答（台账约束）
        facts = _factsheet(result.ranking, top_n=5)
        answer, bad = None, []
        try:
            answer = self._ensure_llm().chat([
                {"role": "system", "content": SYSTEM_ANALYST},
                {"role": "user", "content": "产品：{}\n评分材料:\n{}\n问题：{}".format(result.text, facts, q)},
            ], max_tokens=500).strip()
            bad = guard_check(answer, build_ledger(facts, result.text))
        except Exception as e:
            answer = "（LLM 回答失败: {}）".format(e)
        step("freeform", q, answer[:60] + "…" if len(answer) > 60 else answer)
        return {"kind": "freeform", "answer": answer, "guard": bad, "trace": trace}
