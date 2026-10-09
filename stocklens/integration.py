"""Adapters to the original projects. No upstream source is modified."""
from __future__ import annotations

import importlib
import math
import os
from pathlib import Path
import sys
import types

# Ngăn các bản SDK cũ tự ghi tài liệu trợ lý khi import thư viện.
os.environ.setdefault('VNSTOCK_DISABLE_AGENT_SETUP','1')

import pandas as pd

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
BOT = WORKSPACE / 'taikhoanx10_bot_tele-main' / 'taikhoanx10_bot_tele-main'
MINER = WORKSPACE / 'vn-annual-report-miner-main' / 'vn-annual-report-miner-main'
HOHA = WORKSPACE / 'HoHa-slide-pdf-core-2026-10-09' / 'hoha-slide-pdf-core' / 'servers' / 'fastapi'
DATABASE = WORKSPACE / 'dtata  full toping' / 'analysis_data' / 'stocks_analysis.sqlite'


def prepare_imports():
    for path in (BOT, MINER / 'src', HOHA, WORKSPACE):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    # arminer.__init__ runs an unrelated environment bootstrap that writes .env.
    # Register the package namespace so its actual modules can be used directly.
    if 'arminer' not in sys.modules:
        package = types.ModuleType('arminer')
        package.__path__ = [str(MINER / 'src' / 'arminer')]
        package.__package__ = 'arminer'
        sys.modules['arminer'] = package


prepare_imports()


def module(name):
    return importlib.import_module(name)


def clean(value):
    """Strict JSON: replace non-finite or pandas missing values with null."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if hasattr(value, 'item'):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, str):
        for name in ('VNSTOCK_API_KEY', 'DNSE_API_KEY', 'DNSE_API_SECRET','SERPER_API_KEY','GOOGLE_API_KEY','BRAVE_API_KEY'):
            secret = os.getenv(name)
            if secret:
                value = value.replace(secret, '[REDACTED]')
    return value


def status():
    return {
        'x10_engine': (BOT / 'strategy_engine.py').is_file(),
        'annual_report_miner': (MINER / 'src/arminer/data/catalog.py').is_file(),
        'hoha_renderer': (HOHA / 'services/smart_layout_renderer.py').is_file(),
        'local_database': DATABASE.is_file(),
        'report_engine': (WORKSPACE / 'report_engine/schema.py').is_file() and (WORKSPACE / 'report_engine/charts.py').is_file(),
        'api_key_in_memory': bool(os.getenv('VNSTOCK_API_KEY')),
    }
