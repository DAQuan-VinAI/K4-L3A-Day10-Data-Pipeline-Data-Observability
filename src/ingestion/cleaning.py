from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord, normalize_doi, strip_markup

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def _clean_list(values) -> list[str]:
    cleaned = [normalize_whitespace(str(value)) for value in values or []]
    return list(dict.fromkeys(value for value in cleaned if value))


def build_text_for_embedding(row: pd.Series | dict) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    run_ts = pd.Timestamp(run_date).tz_convert("UTC")

    df = pd.DataFrame([asdict(record) for record in records])
    if df.empty:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df["paper_id"] = df["paper_id"].map(normalize_doi)
    df["title"] = df["title"].fillna("").map(normalize_whitespace)
    df["summary"] = df["summary"].fillna("").map(strip_markup)
    df["authors"] = df["authors"].map(_clean_list)
    df["categories"] = df["categories"].map(_clean_list)
    df["primary_category"] = df["categories"].map(lambda items: items[0] if items else "Uncategorized")

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True).fillna(published)

    # Bo row xau: thieu khoa, thieu noi dung hoac ngay xuat ban khong parse duoc.
    valid = (df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "") & published.notna()
    df, published, updated = df[valid].copy(), published[valid], updated[valid]

    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")
    df["age_days"] = (run_ts - published).dt.days.clip(lower=0).astype(int)

    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len().astype(int)
    df["text_for_embedding"] = df.apply(build_text_for_embedding, axis=1)

    # Khu trung lap theo paper_id: giu ban cap nhat moi nhat.
    df = (
        df.sort_values(["paper_id", "updated"], ascending=[True, False])
        .drop_duplicates(subset="paper_id", keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return df[CLEAN_COLUMNS]
