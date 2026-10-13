"""联网搜索层：三种模式，零强制依赖。

1. SEARCH_API_KEY 配置 → TavilySearch（付费/免费额度 API）
2. 默认 → CrawlSearch：直接抓取 Bing 中国版 / Baidu 结果页（免 API，
   中国网络环境优先可用；抓取失败自动静默降级）
3. DISABLE_CRAWL=1 且无 SEARCH_API_KEY → None（纯 LLM 知识模式）
"""
import html as _html
import os
import re
import time

import requests

from . import envload


class TavilySearch:
    """Tavily 搜索 API（免费额度 1000 次/月；中国本地访问可能需代理，云端通常可达）。"""

    API = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 5):
        resp = requests.post(
            self.API,
            json={"api_key": self.api_key, "query": query, "max_results": max_results},
            timeout=20,
        )
        resp.raise_for_status()
        return [{"title": x.get("title", ""),
                 "content": (x.get("content") or "")[:400],
                 "url": x.get("url", "")}
                for x in resp.json().get("results", [])]


def _strip(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment or "")
    return _html.unescape(re.sub(r"\s+", " ", text)).strip()


def parse_bing_results(html: str, max_results: int = 6):
    """解析 Bing 结果页 <li class="b_algo"> 块（离线可测）。"""
    out = []
    for m in re.finditer(
            r'<li class="b_algo".*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</li>',
            html, re.S):
        url, title_frag = m.group(1), m.group(2)
        snip = re.search(r"<p[^>]*>(.*?)</p>", m.group(0), re.S)
        out.append({"title": _strip(title_frag), "url": url,
                    "content": _strip(snip.group(1))[:400] if snip else ""})
        if len(out) >= max_results:
            break
    return out


def parse_baidu_results(html: str, max_results: int = 6):
    """解析 Baidu 结果页标题链接（摘要结构多变，只取标题+跳转链接）。"""
    out = []
    for m in re.finditer(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        out.append({"title": _strip(m.group(2)), "url": m.group(1), "content": ""})
        if len(out) >= max_results:
            break
    return out


class CrawlSearch:
    """免 API 搜索：直接请求搜索引擎结果页。接口与 TavilySearch 兼容。"""

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

    def search(self, query: str, max_results: int = 6):
        for engine in (self._bing, self._baidu):
            try:
                results = engine(query, max_results)
                if results:
                    return results
            except Exception:
                continue  # 引擎失败换下一个，全失败返回空（上层降级知识模式）
            time.sleep(1)  # 抓取礼仪：引擎切换间隔
        return []

    def _get(self, url, params=None):
        resp = requests.get(url, params=params, timeout=15, headers={
            "User-Agent": self.UA,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml",
        })
        resp.raise_for_status()
        if resp.encoding in (None, "ISO-8859-1"):
            resp.encoding = resp.apparent_encoding
        return resp.text

    def _bing(self, query, max_results):
        html = self._get("https://cn.bing.com/search",
                         params={"q": query, "count": str(max_results)})
        return parse_bing_results(html, max_results)

    def _baidu(self, query, max_results):
        html = self._get("https://www.baidu.com/s",
                         params={"wd": query, "rn": str(max_results)})
        return parse_baidu_results(html, max_results)


def get_search_client():
    """优先级：Tavily（有 key）> 抓取（默认）> None（DISABLE_CRAWL=1）。"""
    envload.load_dotenv()
    key = os.environ.get("SEARCH_API_KEY", "").strip()
    if key:
        return TavilySearch(key)
    if os.environ.get("DISABLE_CRAWL", "").strip() == "1":
        return None
    return CrawlSearch()
