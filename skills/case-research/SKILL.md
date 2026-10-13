---
name: case-research
description: 免API网络案例研究：用代码直接抓取搜索引擎与行业网站，为客户产品提炼特征、在互联网上发现相近品牌并制成出海分析案例卡（无需任何搜索API密钥）。当用户要求"联网找案例/对标品牌/竞品故事"、"给我找个成功案例"，或出海罗盘（ai-race-2026）的案例层需要真实素材时使用。
---

# 免 API 网络案例研究

目标：给定客户的产品/品牌描述，**不使用任何搜索 API**，仅用代码直接抓取网页，找到有共同性、可复制的真实品牌案例，输出结构化案例卡。铁律与出海罗盘一致：**只写你真实访问到或高确信公开存在的品牌，锚点必须是你真实抓取过的 URL 或确定性高的公开事实，抓不到就说抓不到。**

## 流程

### 第 1 步：特征提取（先分析，再上网）

从客户描述提炼 5 类可检索特征，缺少的直接用品类常识补齐并标注假设：

- **品类词**：中文核心词 + 英文对应词（如 空气炸锅 / air fryer）
- **需求场景**：一人食健康烹饪 / 户外便携 / 宠物喂养自动化……
- **目标人群与价位**：预算型 / 中端 / 高端
- **渠道特征**：线上 B2C（亚马逊/独立站/TikTok Shop）/ 线下商超 / 经销
- **差异点**：大容量、便携、智能化、颜值设计……

### 第 2 步：查询设计（每个特征至少 1 条查询）

组合式查询比单词查询有效。中文走国内引擎，英文查询仅在确认网络可达时使用：

- `{品类} 出海 品牌 案例`
- `{品类} 亚马逊 爆款 品牌`
- `{场景} 中国品牌 海外 成功`
- `{英文品类词} Chinese brands global success`

### 第 3 步：抓取（免 API 引擎，按序降级）

在本项目内直接用现成引擎（接口兼容，自动引擎降级 + 抓取间隔）：

```python
from luopan.websearch import CrawlSearch
rows = CrawlSearch().search("{品类} 出海 品牌 案例", max_results=6)
# rows: [{title, url, content}] —— content 可能为空（Baidu 只回标题链接）
```

独立场景（项目外）用同一套请求模板：

```python
import requests, re, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}
def get(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
    return r.text
def strip_html(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))).strip()
# Bing 中国版：<li class="b_algo"> 块内 <h2><a href=标题> + <p>摘要
htmltxt = get("https://cn.bing.com/search", {"q": "空气炸锅 出海 品牌 案例", "count": "10"})
# Baidu 兜底：<h3><a href=标题链接>（摘要结构多变，只取标题）
# htmltxt = get("https://www.baidu.com/s", {"wd": "空气炸锅 出海 品牌 案例", "rn": "10"})
```

**引擎经验**（2026-10 实测）：cn.bing.com 结构最稳但部分网络不返回；baidu.com 兜底成功率高、链接是 `baidu.com/link?url=` 跳转链（作线索够用）；搜索引擎全挂时改抓**垂直站内搜索**（见下）。

### 第 4 步：垂直站点深挖（搜索引擎之外的富矿）

跨境出海垂媒的行业案例密度远高于通用搜索，可直接站内搜索或抓栏目页：

- **白鲸出海** baijingapp.com（品牌出海案例最多）
- **雨果网** cifnews.com（跨境电商实操）
- **亿邦动力** ebrun.com（行业报告向）
- **36氪** 36kr.com（新消费品牌融资与增长故事）
- 目标市场电商榜：亚马逊各国 Best Sellers（亚马逊站点从中国访问不稳定，云端可用）

对搜索结果中信息密度最高的 1-2 条 URL，抓原文并 `strip_html` 后取前 2000-3000 字作为案例证据。

### 第 5 步：品牌候选提炼

从标题/摘要/原文中找**重复出现的品牌词**，为每个候选记录：出现的来源 URL（这就是锚点）、主营品类、被描述的市场与成绩。品牌是否"与客户产品有共同性"按四类判断（可叠加）：同类产品 / 相近需求或技术 / 相近人群 / 相似渠道打法。

### 第 6 步：合成案例卡（对齐出海罗盘 schema）

每案例输出以下字段，市场对照用 `luopan.cases.alignment(markets_iso3, ranked)` 自动计算：

```python
{"brand": "", "origin": "", "relation": "共同性说明",
 "markets": ["市场中文名"], "how_succeeded": "它如何成功 ≤120字",
 "playbook": "客户的品牌如何复制该路径 ≤120字",
 "anchors": "来源：真实抓取过的 URL 或 公司全称/总部/产品线"}
```

与程序化管线集成（推荐，自动缓存+降级）：

```python
from luopan.casefinder import find_cases
from luopan.websearch import CrawlSearch
cases = find_cases(profile, ranked, llm, price_tier="mid", search_client=CrawlSearch())
```

### 第 7 步：诚实底线

- 每张案例卡必须带锚点；**抓取与知识冲突时以抓到的为准，都没有就明说没有**
- 案例成绩不写无法溯源的精确数字（"连续多年位居前列" ✓，"市占率 23.7%" ✗ 除非原文有）
- 向用户展示时注明"来源：网络抓取（附 URL），检索日期"
- 抓取礼仪：请求间隔 ≥1 秒、带 UA、只抓公开页面、结果落盘缓存不重复抓

## 失败降级链

CrawlSearch 引擎失败 → 换引擎 → 全失败返回空 → casefinder 自动落回 **LLM 知识模式**（输出仍要求可查证锚点，但需提示用户"该批案例未经联网核实"）。
