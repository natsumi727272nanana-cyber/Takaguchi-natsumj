"""動作確認用の架空データを作る（実在の顧客・スタッフとは無関係）。

  python samples/make_sample.py samples/data
  python -m salon_kpi build --month 2026-09 --data samples/data --out samples/output
"""
import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

STAFF = {"honten": ["スタイリストA", "スタイリストB", "スタイリストC", "スタイリストD"],
         "chayamachi": ["スタイリストE", "スタイリストF", "スタイリストG"]}
MENUS = [("カット", 5500), ("カット+カラー", 12000), ("カット+カラー+ヘッドスパ", 16500),
         ("カット+パーマ", 14000), ("カラー+トリートメント", 13000), ("ヘッドスパ", 6600)]
SB_HEADER = ["来店日", "お客様番号", "お客様名", "電話番号", "担当スタッフ", "新規/再来", "指名", "メニュー", "会計金額"]


def main(out: Path):
    rnd = random.Random(42)
    start = {"honten": date(2025, 6, 1), "chayamachi": date(2026, 8, 1)}
    end = date(2026, 10, 10)
    for store, first in start.items():
        customers: dict[int, date] = {}
        next_id = 1
        by_month: dict[str, list] = {}
        pay_by_month: dict[str, list] = {}
        d = first
        while d <= end:
            for _ in range(rnd.randint(25, 40) if store == "honten" else rnd.randint(18, 30)):
                regulars = [c for c, last in customers.items() if (d - last).days > 30]
                if regulars and rnd.random() < 0.7:
                    cid, kind = rnd.choice(regulars), "再来"
                else:
                    cid, kind, next_id = next_id, "新規", next_id + 1
                customers[cid] = d
                menu, price = rnd.choice(MENUS)
                staff = rnd.choice(STAFF[store])
                nominated = "指名" if kind == "再来" and rnd.random() < 0.6 else "なし"
                row = [d.strftime("%Y/%m/%d"), f"{store[:2].upper()}{cid:06d}", "（架空）", "000-0000-0000",
                       staff, kind, nominated, menu, f"{price:,}"]
                key = d.strftime("%Y-%m")
                by_month.setdefault(key, []).append(row)
                if rnd.random() < 0.9:  # 1割は現金でAirペイを通らない想定
                    pay_by_month.setdefault(key, []).append([d.strftime("%Y/%m/%d") + " 12:00", "売上", price])
            d += timedelta(days=1)
        for key, rows in by_month.items():
            p = out / "raw" / key / store
            p.mkdir(parents=True, exist_ok=True)
            with open(p / "salonboard.csv", "w", encoding="cp932", newline="") as f:
                f.write("予約・会計一覧\n")  # タイトル行付きの出力を模す
                w = csv.writer(f)
                w.writerow(SB_HEADER)
                w.writerows(rows)
            with open(p / "airpay.csv", "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["決済日時", "取引種別", "決済金額"])
                w.writerows(pay_by_month.get(key, []))
    (out / "manual").mkdir(parents=True, exist_ok=True)
    with open(out / "manual" / "monthly_costs.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "store", "labor_cost", "hpb_cost"])
        w.writerow(["2026-09", "honten", 3_600_000, 450_000])
        w.writerow(["2026-09", "chayamachi", 3_300_000, 380_000])


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "samples/data"))
