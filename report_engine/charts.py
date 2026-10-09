import base64, io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

NAVY, TEAL, ORANGE, GREY, RED, GREEN = "#0B2545", "#13A89E", "#F28C28", "#8D99AE", "#D64545", "#0E9F6E"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "axes.labelcolor": "#444", "xtick.color": "#444", "ytick.color": "#444"})

def _uri(fig) -> str:
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=200, bbox_inches="tight"); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def price_chart(p, sessions=250) -> str:
    df = pd.DataFrame([x.model_dump() for x in p.prices]).set_index("date")
    df.index = pd.to_datetime(df.index)
    for w in (50, 200):
        df[f"ma{w}"] = df["value"].rolling(w).mean()
    d = df.tail(sessions)
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.2, 3.8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    a.plot(d.index, d["value"], color=NAVY, lw=1.4, label="Giá đóng cửa")
    if d["ma50"].notna().any():  a.plot(d.index, d["ma50"], color=TEAL, lw=1, label="MA50")
    if d["ma200"].notna().any(): a.plot(d.index, d["ma200"], color=ORANGE, lw=1, label="MA200")
    for val, lab, col in ((p.target_price, "Giá mục tiêu", RED), (p.support, "Hỗ trợ", GREEN),
                          (p.resistance, "Kháng cự", GREY), (p.trailing_stop, "Trailing stop", ORANGE)):
        if val: a.axhline(val, color=col, ls="--", lw=0.9, label=f"{lab} {val:,.1f}")
    a.legend(frameon=False, fontsize=6.5, ncol=4, loc="upper left")
    b.bar(d.index, d["volume"], color=GREY, width=1.0); b.set_ylabel("KL", fontsize=7)
    return _uri(fig)

def score_chart(p) -> str | None:
    rows = [(n, v) for n, v in (("Thống nhất", p.unified_score), ("FA", p.fa_score), ("TA", p.ta_score)) if v is not None]
    if not rows: return None
    fig, ax = plt.subplots(figsize=(3.4, 1.9))
    names, vals = zip(*rows)
    cols = [GREEN if v >= p.buy_threshold else (RED if v < p.sell_threshold else ORANGE) for v in vals]
    ax.barh(names, vals, color=cols, height=0.5); ax.set_xlim(0, 100); ax.invert_yaxis()
    ax.axvline(p.buy_threshold, color=GREY, ls="--", lw=0.8); ax.text(p.buy_threshold, -0.65, f"Ngưỡng MUA {p.buy_threshold:.0f}", fontsize=6, ha="center")
    for i, v in enumerate(vals): ax.text(v + 1, i, f"{v:.0f}", va="center", fontsize=8)
    return _uri(fig)

def fundamentals_chart(f) -> str | None:
    keys = f.chart_keys or list(f.metrics)[:2]
    if not keys: return None
    fig, ax = plt.subplots(figsize=(3.7, 2.7)); x = range(len(f.periods)); w = 0.38
    bars = keys[:2]
    for i, k in enumerate(bars):
        vals = [v if v is not None else 0 for v in f.metrics[k]]
        off = (i - (len(bars) - 1) / 2) * w
        ax.bar([j + off for j in x], vals, w, color=(NAVY, TEAL)[i], label=k)
    ax.set_xticks(list(x)); ax.set_xticklabels(f.periods, fontsize=7); ax.legend(frameon=False, fontsize=7, loc="upper left")
    if len(keys) > 2:
        ax2 = ax.twinx(); line = f.metrics[keys[2]]
        ax2.plot(list(x), [v if v is not None else float("nan") for v in line], color=ORANGE, marker="o", lw=1.2)
        ax2.set_ylabel(keys[2], fontsize=7); ax2.spines["top"].set_visible(False)
    return _uri(fig)

def football_chart(p) -> str | None:
    if not p.valuation or not p.valuation.methods: return None
    ms = p.valuation.methods
    fig, ax = plt.subplots(figsize=(7.2, 0.7 + 0.5 * len(ms)))
    for i, m in enumerate(ms):
        ax.barh(i, m.high - m.low, left=m.low, color=TEAL if i % 2 == 0 else NAVY, height=0.5)
        ax.text(m.high, i, f" {m.low:,.1f}–{m.high:,.1f}", va="center", fontsize=7)
    ax.set_yticks(range(len(ms))); ax.set_yticklabels([m.name for m in ms], fontsize=8); ax.invert_yaxis()
    ax.axvline(p.price, color=GREY, ls="--"); ax.text(p.price, len(ms) - 0.35, "Giá hiện tại", fontsize=7, ha="center")
    if p.target_price:
        ax.axvline(p.target_price, color=RED); ax.text(p.target_price, -0.7, "Giá mục tiêu", fontsize=7, ha="center", color=RED)
    return _uri(fig)

def equity_chart(p) -> str | None:
    if not p.backtest or len(p.backtest.equity) < 5: return None
    e = p.backtest.equity
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.plot([x.date for x in e], [x.value for x in e], color=TEAL, lw=1.4)
    ax.fill_between([x.date for x in e], [x.value for x in e], min(x.value for x in e), color=TEAL, alpha=0.1)
    ax.set_ylabel("NAV (chuẩn hóa)", fontsize=8)
    return _uri(fig)