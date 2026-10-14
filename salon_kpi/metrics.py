"""KPIの計算。定義は README の「KPI定義」と一致させること。"""
from __future__ import annotations

import pandas as pd

KPI_LABELS = {
    "sales": "売上",
    "visits": "客数",
    "new_customers": "新規客数",
    "repeat_customers": "既存客数",
    "avg_ticket": "客単価",
    "new_return_rate": "新規再来率",
    "nomination_rate": "指名率",
    "spa_rate": "スパ付帯率",
    "labor_cost_ratio": "人件費率",
    "hpb_cost_per_new": "新規1人あたりHPB費",
}


def _div(a, b):
    return (a / b).where(b > 0)


def new_return_flags(visits: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """新規来店ごとに、同じ店で window_days 日以内に再来したかを判定する。

    matured=False は観測期間が足りず未確定（データ最終日 < 初回来店日 + window）。
    """
    v = visits[visits["customer_key"] != ""]
    new = visits[visits["is_new"]].copy()
    last_date = visits["date"].max()
    later = v[["store", "customer_key", "date"]].rename(columns={"date": "next_date"})
    m = new.reset_index().merge(later, on=["store", "customer_key"], how="left")
    m = m[(m["next_date"] > m["date"]) & (m["next_date"] <= m["date"] + pd.Timedelta(days=window_days))]
    new["returned"] = new.index.isin(m["index"])
    new["matured"] = new["date"] + pd.Timedelta(days=window_days) <= last_date
    return new


def compute(visits: pd.DataFrame, costs: pd.DataFrame, airpay: pd.DataFrame, window_days: int,
            by: list[str]) -> pd.DataFrame:
    """by=["month","store"] で店舗別、["month","store","staff"] でスタイリスト別。"""
    g = visits.groupby(by)
    out = pd.DataFrame({
        "sales": g["sales"].sum(),
        "visits": g.size(),
        "new_customers": g["is_new"].sum(),
        "nominated": g["is_nominated"].sum(),
        "spa": g["has_spa"].sum(),
    })
    out["repeat_customers"] = out["visits"] - out["new_customers"]
    out["avg_ticket"] = _div(out["sales"], out["visits"])
    out["nomination_rate"] = _div(out["nominated"], out["visits"])
    out["spa_rate"] = _div(out["spa"], out["visits"])

    # 新規再来率：その月に新規で来た人のうち、window日以内に再来した割合（担当は初回担当）
    flags = new_return_flags(visits, window_days)
    if len(flags):
        fg = flags.groupby(by)
        out["new_cohort"] = fg.size()
        out["new_returned"] = fg["returned"].sum()
        out["new_return_matured"] = fg["matured"].all()
    else:
        out["new_cohort"], out["new_returned"], out["new_return_matured"] = 0, 0, False
    out["new_return_rate"] = _div(out["new_returned"], out["new_cohort"]).where(out["new_return_matured"].astype(bool))
    out = out.reset_index()

    if "staff" not in by:  # 人件費・HPB費・Airペイは店舗単位でしか持たない
        out = out.merge(costs, on=["month", "store"], how="left").merge(airpay, on=["month", "store"], how="left")
        out["labor_cost_ratio"] = _div(out["labor_cost"], out["sales"])
        out["hpb_cost_per_new"] = _div(out["hpb_cost"], out["new_customers"])
        out["airpay_diff"] = out["airpay_sales"] - out["sales"]
        out = out.sort_values(["store", "month"])
        out["sales_mom"] = _div(out["sales"], out.groupby("store")["sales"].shift(1)) - 1
        prev_year = out[["store", "month", "sales"]].copy()
        prev_year["month"] = (pd.to_datetime(prev_year["month"]) + pd.DateOffset(years=1)).dt.strftime("%Y-%m")
        out = out.merge(prev_year.rename(columns={"sales": "sales_prev_year"}), on=["store", "month"], how="left")
        out["sales_yoy"] = _div(out["sales"], out["sales_prev_year"]) - 1
    return out
