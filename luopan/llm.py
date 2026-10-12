"""OpenAI-compatible LLM client（.env / 环境变量注入，密钥不落代码不落 git）。"""
import os
import time

import requests

from . import envload


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=90):
        envload.load_dotenv()
        self.base = (base_url or os.environ.get("LLM_BASE_URL") or "").rstrip("/")
        self.key = api_key or os.environ.get("LLM_API_KEY") or ""
        self.model = model or os.environ.get("LLM_MODEL") or ""
        self.timeout = timeout
        if not (self.base and self.key and self.model):
            raise LlmError("LLM 未配置：需要 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL（.env 或环境变量）")

    def chat(self, messages, temperature=0.0, max_tokens=2000):
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        last = None
        for wait in (0, 3, 9):  # 401/400 等客户端错立即抛出，只对网络/限流重试
            if wait:
                time.sleep(wait)
            try:
                resp = requests.post(self.base + "/chat/completions",
                                     headers=headers, json=payload, timeout=self.timeout)
            except requests.RequestException as e:
                last = e
                continue
            if resp.status_code in (429, 502, 503):
                last = LlmError("llm http {}: {}".format(resp.status_code, resp.text[:120]))
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        raise LlmError("llm 连续失败: {}".format(last))
