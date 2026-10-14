"""CSVの読み込み・列名の対応付け・個人情報の除去。

方針:
- 設定で定義した列だけを取り出し、それ以外（氏名・電話番号・メール等）は読み込み直後に捨てる。
- お客様番号は再来判定にだけ使い、ソルト付きハッシュに置き換えてから保持する。
- メニュー名はスパ判定にだけ使い、保持しない。
"""
from __future__ import annotations

import csv
import hashlib
import io
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8-sig", "cp932")
SALT_FILE = Path(".salt")


@dataclass
class LoadReport:
    """データチェック用の記録（値は持たず、列名とファイル名だけ）。"""

    file: str
    matched: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    dropped_columns: list[str] = field(default_factory=list)
    rows: int = 0


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path}: 文字コードを判別できません（UTF-8 / Shift_JIS 以外）")


def _find_header_row(rows: list[list[str]], candidates: dict[str, list[str]]) -> int:
    """先頭にタイトル行がある出力に備え、既知の列名を2つ以上含む最初の行を見出しとみなす。"""
    known = {c for cands in candidates.values() for c in cands}
    for i, row in enumerate(rows[:15]):
        if sum(1 for cell in row if cell.strip() in known) >= 2:
            return i
    return 0


def read_csv(path: Path, candidates: dict[str, list[str]]) -> tuple[pd.DataFrame, LoadReport]:
    text = _decode(path)
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = _find_header_row(rows, candidates)
    df = pd.read_csv(io.StringIO(text), skiprows=header_idx, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]

    report = LoadReport(file=str(path), rows=len(df))
    out = pd.DataFrame(index=df.index)
    for key, cands in candidates.items():
        hit = next((c for c in cands if c in df.columns), None)
        if hit is None:
            report.missing.append(key)
        else:
            report.matched[key] = hit
            out[key] = df[hit].str.strip()
    report.dropped_columns = [c for c in df.columns if c not in report.matched.values()]
    return out, report


def load_salt() -> bytes:
    if not SALT_FILE.exists():
        SALT_FILE.write_text(secrets.token_hex(32))
    return SALT_FILE.read_text().strip().encode()


def pseudonymize(series: pd.Series, salt: bytes, store: str) -> pd.Series:
    # SALON BOARDは店舗ごとにアカウントが分かれている前提で、店舗IDも混ぜる
    def h(v: str) -> str:
        if not v:
            return ""
        return hashlib.sha256(salt + store.encode() + b"|" + v.encode()).hexdigest()[:16]

    return series.map(h)


def to_number(series: pd.Series) -> pd.Series:
    cleaned = series.str.replace(r"[,¥￥円\s]", "", regex=True).replace("", "0")
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.str.slice(0, 10).str.replace("/", "-"), errors="coerce")
