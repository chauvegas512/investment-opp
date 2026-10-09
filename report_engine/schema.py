"""Hợp đồng dữ liệu (data contract) của PDF engine.

Nguyên tắc:
- Engine KHÔNG tự tính điểm/khuyến nghị: X10 tính, engine chỉ trình bày.
- Trường tùy chọn = None/[] thì mục tương ứng trong PDF tự ẩn (không điền số giả).
- NaN/Inf bị chặn ở đây để không lọt chuỗi "nan" vào PDF.
Yêu cầu: pydantic >= 2.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Finite = Annotated[float, Field(allow_inf_nan=False)]
Status = Literal["good", "bad", "neutral"]


def _nan_to_none(x):
    """pandas hay sinh NaN cho ô thiếu; chuyển thành None để engine hiển thị '—'."""
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


class KV(BaseModel):
    label: str
    value: str


class Signal(BaseModel):
    label: str
    value: str
    status: Status = "neutral"
    note: str = ""


class Point(BaseModel):
    """Một điểm chuỗi thời gian. value = giá đóng cửa (hoặc NAV với đường vốn)."""
    date: dt.date
    value: Finite
    volume: Finite = 0.0


class Fundamentals(BaseModel):
    periods: list[str]
    metrics: dict[str, list[Optional[Finite]]]
    units: dict[str, str] = {}
    chart_keys: list[str] = []  # tối đa 3: 2 cột + 1 đường (trục phải)

    @field_validator("metrics", mode="before")
    @classmethod
    def _clean(cls, v):
        if isinstance(v, dict):
            return {k: [_nan_to_none(x) for x in vals] for k, vals in v.items()}
        return v

    @model_validator(mode="after")
    def _check(self):
        for k, vals in self.metrics.items():
            if len(vals) != len(self.periods):
                raise ValueError(
                    f"metrics['{k}'] có {len(vals)} giá trị nhưng có {len(self.periods)} kỳ"
                )
        for k in self.chart_keys:
            if k not in self.metrics:
                raise ValueError(f"chart_keys chứa '{k}' không có trong metrics")
        if len(self.chart_keys) > 3:
            raise ValueError("chart_keys tối đa 3 phần tử")
        return self


class ValMethod(BaseModel):
    name: str
    low: Finite
    high: Finite

    @model_validator(mode="after")
    def _order(self):
        if self.low > self.high:
            raise ValueError(f"Khoảng định giá '{self.name}': low > high")
        return self


class Valuation(BaseModel):
    methods: list[ValMethod]
    assumptions: dict[str, str] = {}


class Backtest(BaseModel):
    period: str
    cagr: Optional[Finite] = None          # %
    max_drawdown: Optional[Finite] = None  # % (số âm)
    win_rate: Optional[Finite] = None      # %
    trades: Optional[int] = None
    fee_note: str = ""
    equity: list[Point] = []               # NAV đã chuẩn hóa

    @model_validator(mode="after")
    def _sane(self):
        if self.max_drawdown is not None and self.max_drawdown > 0:
            raise ValueError("max_drawdown phải là số âm hoặc 0 (đơn vị %)")
        if self.win_rate is not None and not 0 <= self.win_rate <= 100:
            raise ValueError("win_rate phải nằm trong 0-100 (%)")
        return self


class NewsItem(BaseModel):
    title: str
    source: str
    date: Optional[str] = None
    url: Optional[str] = None


class SourceNote(BaseModel):
    item: str
    source: str
    as_of: str


class Payload(BaseModel):
    # --- nhận diện ---
    ticker: str
    company: str
    exchange: str = ""
    sector: str = ""
    report_date: dt.date
    data_as_of: dt.date
    is_demo: bool = False  # True -> đóng dấu "DỮ LIỆU MẪU" trên mọi trang

    # --- khuyến nghị do X10 quyết định ---
    rating: str = "KHÔNG ĐỦ DỮ LIỆU"        # MUA / NẮM GIỮ / BÁN ...
    unified_score: Optional[Finite] = None  # 0-100
    fa_score: Optional[Finite] = None
    ta_score: Optional[Finite] = None
    buy_threshold: Finite = 60
    sell_threshold: Finite = 35
    market_state: str = ""

    # --- giá ---
    price: Finite
    change_pct: Optional[Finite] = None
    target_price: Optional[Finite] = None   # None -> ẩn Giá mục tiêu/Upside
    horizon: str = "12 tháng"
    key_stats: list[KV] = []

    # --- kỹ thuật ---
    prices: list[Point]
    support: Optional[Finite] = None
    resistance: Optional[Finite] = None
    trailing_stop: Optional[Finite] = None
    signals: list[Signal] = []

    # --- các mục tùy chọn ---
    fundamentals: Optional[Fundamentals] = None
    valuation: Optional[Valuation] = None
    backtest: Optional[Backtest] = None

    # --- diễn giải ---
    thesis: list[str] = []
    risks: list[str] = []
    news: list[NewsItem] = []
    sources: list[SourceNote] = []
    warnings: list[str] = []

    # ---------- kiểm tra ----------
    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("ticker rỗng")
        return v

    @field_validator("price")
    @classmethod
    def _price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price phải là số dương")
        return v

    @field_validator("unified_score", "fa_score", "ta_score")
    @classmethod
    def _score_range(cls, v):
        if v is not None and not 0 <= v <= 100:
            raise ValueError("điểm phải nằm trong 0-100")
        return v

    @model_validator(mode="after")
    def _consistency(self):
        if len(self.prices) < 30:
            raise ValueError("Cần ít nhất 30 phiên giá để vẽ biểu đồ")
        dates = [p.date for p in self.prices]
        if dates != sorted(dates):
            raise ValueError("prices phải sắp theo ngày tăng dần")
        if len(set(dates)) != len(dates):
            raise ValueError("prices có ngày trùng lặp")
        if self.data_as_of < dates[-1]:
            raise ValueError("data_as_of sớm hơn phiên giá cuối cùng")
        if self.report_date < self.data_as_of:
            raise ValueError("report_date sớm hơn data_as_of")
        if self.target_price is not None and self.target_price <= 0:
            raise ValueError("target_price phải là số dương")
        if self.sell_threshold >= self.buy_threshold:
            raise ValueError("sell_threshold phải nhỏ hơn buy_threshold")
        return self

    @property
    def upside(self) -> Optional[float]:
        """Tỷ lệ tăng/giảm so với giá mục tiêu (0.18 = +18%); None nếu không có giá mục tiêu."""
        return None if self.target_price is None else self.target_price / self.price - 1