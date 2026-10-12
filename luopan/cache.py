"""本地 JSON 缓存：断网可重跑、Comtrade 匿名额度跨天续用。"""
import json
import time

from . import config


def _path(source: str, key: str):
    return config.CACHE_DIR / source / f"{key}.json"


def get(source: str, key: str):
    p = _path(source, key)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def put(source: str, key: str, params: dict, data) -> None:
    p = _path(source, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "params": params, "data": data}
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
