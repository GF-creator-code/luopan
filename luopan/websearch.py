"""可选联网搜索层：配置 SEARCH_API_KEY 后自动启用（Tavily 协议）。

无 key 时 get_search_client() 返回 None，上层走 LLM 知识模式——
不硬依赖任何未配置的外部服务。
"""
import os

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


def get_search_client():
    envload.load_dotenv()
    key = os.environ.get("SEARCH_API_KEY", "").strip()
    return TavilySearch(key) if key else None
