"""LlmClient 韧性单测：非 JSON 响应重试、空内容报错（零网络）。"""
import pytest
import requests

from luopan.llm import LlmClient, LlmError


class _FakeResp:
    def __init__(self, status=200, text="", payload=None):
        self.status_code = status
        self.text = text
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _client():
    return LlmClient(base_url="https://x.example/v1", api_key="k", model="m")


def test_chat_retries_on_non_json(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(1)
        if len(calls) == 1:
            return _FakeResp(200, "<html>gateway error</html>", None)  # 首次非 JSON
        return _FakeResp(200, "ok", {"choices": [{"message": {"content": "正常"}}]})

    monkeypatch.setattr("luopan.llm.requests.post", fake_post)
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    assert _client().chat([{"role": "user", "content": "hi"}]) == "正常"
    assert len(calls) == 2  # 第一次失败后重试成功


def test_chat_empty_content_raises(monkeypatch):
    monkeypatch.setattr("luopan.llm.requests.post",
                        lambda *a, **k: _FakeResp(200, "", {"choices": [{"message": {"content": "  "}}]}))
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    with pytest.raises(LlmError):
        _client().chat([{"role": "user", "content": "hi"}])


def test_chat_all_non_json_exhausts_retries(monkeypatch):
    monkeypatch.setattr("luopan.llm.requests.post",
                        lambda *a, **k: _FakeResp(200, "err", None))
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    with pytest.raises(LlmError):
        _client().chat([{"role": "user", "content": "hi"}])


SSE_BODY = (
    'data: {"id":"x","object":"chat.completion.chunk","choices":[{"index":0,'
    '"delta":{"content":"你"},"finish_reason":null}]}\n\n'
    'data: {"id":"x","object":"chat.completion.chunk","choices":[{"index":0,'
    '"delta":{"content":"好"},"finish_reason":"stop"}]}\n\n'
    'data: [DONE]\n\n'
)


def test_chat_parses_buffered_sse(monkeypatch):
    """网关把流式协议整体返回时，按 SSE 拼出完整内容（实测 OneTop 高负载行为）。"""
    monkeypatch.setattr("luopan.llm.requests.post",
                        lambda *a, **k: _FakeResp(200, SSE_BODY, None))
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    assert _client().chat([{"role": "user", "content": "hi"}]) == "你好"


def test_fallback_endpoint_used_when_primary_down(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if "x.example" in url:
            raise requests.ConnectionError("primary down")
        return _FakeResp(200, "ok", {"choices": [{"message": {"content": "兜底"}}]})

    monkeypatch.setattr("luopan.llm.requests.post", fake_post)
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    c = _client()
    c.fallback = {"base": "https://fallback.example/v1", "key": "k2", "model": "m2"}
    assert c.chat([{"role": "user", "content": "hi"}]) == "兜底"
    assert any("fallback.example" in u for u in calls)


def test_no_fallback_raises_original(monkeypatch):
    monkeypatch.setattr("luopan.llm.requests.post",
                        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("down")))
    monkeypatch.setattr("luopan.llm.time.sleep", lambda s: None)
    with pytest.raises(LlmError):
        _client().chat([{"role": "user", "content": "hi"}])
