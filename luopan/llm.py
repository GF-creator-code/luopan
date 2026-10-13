"""OpenAI-compatible LLM client（.env / 环境变量注入，密钥不落代码不落 git）。

兼容两类响应：标准 JSON，以及网关在缓冲模式下把流式协议整体返回的
SSE 文本（`data: {...}` 逐块拼接）——实测 OneTop 高负载时会触发。
"""
import json
import os
import time

import requests

from . import envload


class LlmError(RuntimeError):
    pass


def _parse_sse_content(text):
    """从 SSE 文本中拼接 content/delta.content；解析不出返回空串。"""
    parts = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk or chunk == "[DONE]":
            continue
        try:
            obj = json.loads(chunk)
        except ValueError:
            continue
        for ch in (obj.get("choices") or []):
            delta = ch.get("delta") or {}
            msg = ch.get("message") or {}
            piece = delta.get("content") or msg.get("content") or ""
            if piece:
                parts.append(piece)
    return "".join(parts)


class LlmClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=45):
        envload.load_dotenv()
        self.base = (base_url or os.environ.get("LLM_BASE_URL") or "").rstrip("/")
        self.key = api_key or os.environ.get("LLM_API_KEY") or ""
        self.model = model or os.environ.get("LLM_MODEL") or ""
        self.timeout = timeout or 90
        if not (self.base and self.key and self.model):
            raise LlmError("LLM 未配置：需要 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL（.env 或环境变量）")
        # 备用通道（可选）：主通道全部重试失败后自动切换
        fb_base = os.environ.get("LLM_FB_BASE_URL", "").rstrip("/")
        fb_key = os.environ.get("LLM_FB_API_KEY", "")
        fb_model = os.environ.get("LLM_FB_MODEL", "")
        self.fallback = {"base": fb_base, "key": fb_key, "model": fb_model} \
            if (fb_base and fb_key and fb_model) else None

    def _post_chat(self, base, key, model, messages, temperature, max_tokens, timeout):
        """对一个端点做 3 次退避尝试；成功返回内容，失败抛 LlmError。"""
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "stream": False,
                   "temperature": temperature, "max_tokens": max_tokens}
        last = None
        for wait in (0, 3, 9):
            if wait:
                time.sleep(wait)
            try:
                resp = requests.post(base + "/chat/completions",
                                     headers=headers, json=payload, timeout=timeout)
            except requests.RequestException as e:
                last = e
                continue
            if resp.status_code in (429, 502, 503):
                last = LlmError("http {}: {}".format(resp.status_code, resp.text[:120]))
                continue
            resp.raise_for_status()
            try:
                data = resp.json()
            except ValueError:
                # 网关缓冲模式可能把流式 SSE 整体返回（实测 OneTop）——先按 SSE 解析
                content = _parse_sse_content(resp.text)
                if content.strip():
                    return content
                last = LlmError("返回非 JSON 也非 SSE（网关错误页/空响应）: {}".format(
                    resp.text[:120]))
                continue
            content = ""
            if isinstance(data, dict) and data.get("choices"):
                content = (data["choices"][0].get("message") or {}).get("content") or ""
            if not content.strip():
                raise LlmError("模型返回空内容（可能 token 上限被推理消耗，或触发安全策略）")
            return content
        raise LlmError("连续失败: {}".format(last))

    def chat(self, messages, temperature=0.0, max_tokens=4000, timeout=None):
        # 默认 4000：deepseek-v4-pro 等推理模型会先消耗推理 token 再输出正文；
        # timeout 可按调用覆盖（长生成如点评/案例给 180s，快调用保持默认 90s）
        eff_timeout = timeout or self.timeout
        # 默认 4000：deepseek-v4-pro 等推理模型会先消耗推理 token 再输出正文
        try:
            return self._post_chat(self.base, self.key, self.model,
                                   messages, temperature, max_tokens, eff_timeout)
        except LlmError as primary_err:
            if self.fallback:
                try:
                    return self._post_chat(self.fallback["base"], self.fallback["key"],
                                           self.fallback["model"], messages,
                                           temperature, max_tokens, eff_timeout)
                except LlmError as fb_err:
                    raise LlmError("主通道失败({})；备用通道也失败({})".format(primary_err, fb_err))
            raise
