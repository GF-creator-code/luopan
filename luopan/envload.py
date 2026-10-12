"""最小 .env 加载器：key=value 行、# 注释；已存在的环境变量不覆盖。"""
import os
from pathlib import Path

from .config import ROOT

_loaded = False


def load_dotenv(path=None):
    global _loaded
    if _loaded:
        return
    p = Path(path) if path else ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    _loaded = True
