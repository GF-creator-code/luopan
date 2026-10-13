"""CrawlSearch 离线解析单测（不联网）。"""
from luopan.websearch import parse_baidu_results, parse_bing_results

BING_HTML = """
<ol id="b_results">
<li class="b_algo" data-bm="1"><h2><a href="https://example.com/a" h="ID=SERP,1">便携咖啡机出海品牌盘点</a></h2>
<div class="b_caption"><p>便携咖啡机品牌 Wacaco、HiBREW 等在欧美市场表现突出……</p></div></li>
<li class="b_algo" data-bm="2"><h2><a href="https://example.com/b">2026 年小家电出口报告</a></h2>
<div class="b_caption"><p>咖啡机品类出口额同比增长。</p></div></li>
</ol>
"""


def test_parse_bing_extracts_title_url_snippet():
    rows = parse_bing_results(BING_HTML, max_results=5)
    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/a"
    assert "便携咖啡机出海品牌盘点" in rows[0]["title"]
    assert "Wacaco" in rows[0]["content"]


def test_parse_bing_respects_max_results():
    assert len(parse_bing_results(BING_HTML, max_results=1)) == 1


def test_parse_baidu_title_links():
    html = '<div><h3 class="t"><a href="http://bd.example/x">扫地机器人 出海</a></h3></div>'
    rows = parse_baidu_results(html)
    assert rows[0]["title"] == "扫地机器人 出海"
    assert rows[0]["url"] == "http://bd.example/x"


def test_parse_empty_page_returns_empty():
    assert parse_bing_results("<html><body>no results</body></html>") == []
    assert parse_baidu_results("") == []
