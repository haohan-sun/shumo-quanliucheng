"""Keep pytest temp data inside the workspace and isolate concurrent agent runs."""
from __future__ import annotations

import os
from pathlib import Path


def pytest_configure(config):
    root = Path(__file__).resolve().parents[2]
    cache_root = root / '90_工具与配置/.cache'
    cache_root.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = cache_root / f'pytest-{os.getpid()}'
