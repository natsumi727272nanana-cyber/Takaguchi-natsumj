"""使い方:
  python -m salon_kpi inspect                 # 実CSVの列名がどう対応したか確認（初回必須）
  python -m salon_kpi build --month 2026-09   # output/kpi_2026-09.xlsx を作成
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import pandas as pd

from .ingest import load_airpay, load_costs, load_visits
from .metrics import compute
from .report import write_report


def _warnings(visits, store_kpi, month, config) -> list[str]:
    w = []
    if visits.empty:
        return ["来店データが0件です。data/raw/<YYYY-MM>/<店舗>/salonboard*.csv を確認してください"]
    first = visits["date"].min()
    w.append(f"データ期間: {first:%Y-%m-%d} 〜 {visits['date'].max():%Y-%m-%d}")
    last = visits["date"].max()
    if last < pd.Period(month, "M").end_time.normalize():
        w.append(f"{month} はデータが {last:%m/%d} までしかありません（月途中の数字です）")
    cur = store_kpi[store_kpi["month"] == month]
    for _, r in cur.iterrows():
        name = config["stores"][r["store"]]
        if r.get("labor_cost") != r.get("labor_cost"):  # NaN
            w.append(f"{name}: {month} の人件費が未入力（人件費率を出せません）")
        diff = r.get("airpay_diff")
        if diff == diff and diff is not None and abs(diff) > 0.02 * r["sales"]:
            w.append(f"{name}: SALON BOARD売上とAirペイ決済額が2%以上ずれています（差額 {diff:,.0f}円）。"
                     "現金・未登録の会計・税込/税抜の違いを確認")
    if (visits["customer_key"] == "").all():
        w.append("お客様番号の列が見つからず、新規再来率を計算できません")
    return w


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="salon_kpi")
    p.add_argument("command", choices=["inspect", "build"])
    p.add_argument("--month", help="対象月 YYYY-MM（build時）")
    p.add_argument("--config", default="config.toml")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="output")
    a = p.parse_args(argv)

    config = tomllib.loads(Path(a.config).read_text(encoding="utf-8"))
    raw = Path(a.data) / "raw"
    if not raw.is_dir():
        print(f"{raw} がありません。README の「フォルダ構成」を参照してください", file=sys.stderr)
        return 1

    visits, sb_reports = load_visits(raw, config)
    airpay, ap_reports = load_airpay(raw, config)

    if a.command == "inspect":
        for r in sb_reports + ap_reports:
            print(f"\n[{r.file}] {r.rows}行")
            for k, v in r.matched.items():
                print(f"  OK  {k:12s} ← {v}")
            for k in r.missing:
                print(f"  --  {k:12s} 見つからない（config.toml に列名を追記）")
            print(f"  読み捨てる列: {', '.join(r.dropped_columns) or 'なし'}")
        return 0

    if not a.month:
        p.error("build には --month YYYY-MM が必要です")
    costs = load_costs(Path(a.data) / "manual" / "monthly_costs.csv")
    window = config["rules"]["repeat_window_days"]
    store_kpi = compute(visits, costs, airpay, window, ["month", "store"])
    staff_kpi = compute(visits, costs, airpay, window, ["month", "store", "staff"])
    out = Path(a.out) / f"kpi_{a.month}.xlsx"
    warnings = _warnings(visits, store_kpi, a.month, config)
    write_report(out, a.month, config, store_kpi, staff_kpi, sb_reports + ap_reports, warnings)
    print(f"作成: {out}")
    for w in warnings:
        print("  ⚠ " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
