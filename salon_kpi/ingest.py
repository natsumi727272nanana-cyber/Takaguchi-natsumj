"""data/raw/<YYYY-MM>/<store>/ 以下のCSVを全期間読み込み、来店単位の表にする。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loader import LoadReport, load_salt, pseudonymize, read_csv, to_date, to_number

VISIT_COLUMNS = ["date", "month", "store", "staff", "customer_key", "is_new", "is_nominated", "has_spa", "sales"]


def _store_dirs(raw_dir: Path, stores: dict[str, str]):
    for month_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        for store_id in stores:
            d = month_dir / store_id
            if d.is_dir():
                yield store_id, d


def load_visits(raw_dir: Path, config: dict) -> tuple[pd.DataFrame, list[LoadReport]]:
    rules = config["rules"]
    cands = config["salonboard"]["columns"]
    salt = load_salt()
    frames, reports = [], []

    for store_id, d in _store_dirs(raw_dir, config["stores"]):
        for path in sorted(d.glob("salonboard*.csv")):
            df, rep = read_csv(path, cands)
            reports.append(rep)
            if "date" not in df or "sales" not in df:
                continue  # 必須列なし。データチェックシートに表示される

            menu = df.get("menu", pd.Series("", index=df.index))
            v = pd.DataFrame({
                "date": to_date(df["date"]),
                "store": store_id,
                "staff": df.get("staff", pd.Series("（未設定）", index=df.index)).replace("", "（未設定）"),
                "customer_key": pseudonymize(df.get("customer_id", pd.Series("", index=df.index)), salt, store_id),
                "visit_type": df.get("visit_type", pd.Series("", index=df.index)),
                "is_nominated": df.get("nominated", pd.Series("", index=df.index)).isin(rules["nominated_values"]),
                "has_spa": menu.str.contains("|".join(rules["spa_keywords"]), regex=True),
                "sales": to_number(df["sales"]),
                "receipt_id": df.get("receipt_id", pd.Series("", index=df.index)),
            })
            # 1会計が複数行（メニュー明細）で出る形式なら、伝票番号で1来店にまとめる。
            # 担当は先頭行のスタッフ（＝メイン担当）に帰属させる。
            if (v["receipt_id"] != "").any():
                v = v.groupby("receipt_id", sort=False).agg(
                    date=("date", "first"), store=("store", "first"), staff=("staff", "first"),
                    customer_key=("customer_key", "first"), visit_type=("visit_type", "first"),
                    is_nominated=("is_nominated", "any"), has_spa=("has_spa", "any"), sales=("sales", "sum"),
                ).reset_index()
            frames.append(v.dropna(subset=["date"]))

    if not frames:
        return pd.DataFrame(columns=VISIT_COLUMNS), reports

    visits = pd.concat(frames, ignore_index=True).sort_values("date", kind="stable")
    has_type = visits["visit_type"] != ""
    flagged_new = visits["visit_type"].isin(rules["new_values"])
    # 来店区分列が無い行は「この店で最初に見たお客様番号」を新規とみなす（過去データが少ないと過大になる）
    first_seen = ~visits.duplicated(["store", "customer_key"]) & (visits["customer_key"] != "")
    visits["is_new"] = flagged_new.where(has_type, first_seen)
    visits["month"] = visits["date"].dt.strftime("%Y-%m")
    return visits[VISIT_COLUMNS].reset_index(drop=True), reports


def load_airpay(raw_dir: Path, config: dict) -> tuple[pd.DataFrame, list[LoadReport]]:
    cands = config["airpay"]["columns"]
    refund = "|".join(config["rules"]["airpay_refund_values"])
    rows, reports = [], []
    for store_id, d in _store_dirs(raw_dir, config["stores"]):
        for path in sorted(d.glob("airpay*.csv")):
            df, rep = read_csv(path, cands)
            reports.append(rep)
            if "date" not in df or "amount" not in df:
                continue
            amount = to_number(df["amount"]).abs()
            if "status" in df:
                amount = amount.where(~df["status"].str.contains(refund, regex=True), -amount)
            rows.append(pd.DataFrame({"month": to_date(df["date"]).dt.strftime("%Y-%m"), "store": store_id, "amount": amount}))
    if not rows:
        return pd.DataFrame(columns=["month", "store", "airpay_sales"]), reports
    pay = pd.concat(rows).dropna(subset=["month"])
    return pay.groupby(["month", "store"], as_index=False)["amount"].sum().rename(columns={"amount": "airpay_sales"}), reports


def load_costs(path: Path) -> pd.DataFrame:
    """手入力の月次コスト（人件費・HPB掲載費）。店舗単位のみ。"""
    cols = ["month", "store", "labor_cost", "hpb_cost"]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, dtype={"month": str, "store": str})
    for c in ("labor_cost", "hpb_cost"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    return df[cols]
