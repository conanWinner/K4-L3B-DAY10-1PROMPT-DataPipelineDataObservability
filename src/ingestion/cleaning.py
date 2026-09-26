from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
]


def clean_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", value))


def _clean_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned = []
    for value in values:
        text = clean_text(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def build_text_for_embedding(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
            f"Published: {row['published']}",
            f"Summary: {row['summary']}",
        ]
    )


def add_derived_columns(df: pd.DataFrame, run_date: datetime) -> pd.DataFrame:
    df = df.copy()
    published = pd.to_datetime(df["published"], errors="coerce")
    df["published"] = published.dt.strftime("%Y-%m-%d")
    run_day = pd.Timestamp(run_date.date())
    df["age_days"] = (run_day - published).dt.days
    df["authors_joined"] = df["authors"].apply(compact_join)
    df["categories_joined"] = df["categories"].apply(compact_join)
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = df.apply(build_text_for_embedding, axis=1)
    return df


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    df = pd.DataFrame([asdict(record) for record in records])
    if df.empty:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    for column in ["paper_id", "title", "summary", "primary_category", "abs_url", "pdf_url", "comment"]:
        df[column] = df[column].apply(clean_text)
    df["paper_id"] = df["paper_id"].str.lower()
    df["authors"] = df["authors"].apply(_clean_list)
    df["categories"] = df["categories"].apply(_clean_list)
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce").dt.strftime("%Y-%m-%d")

    df = add_derived_columns(df, run_date)
    df = df[(df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "")]
    df = df.dropna(subset=["published", "age_days"])
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df["age_days"] = df["age_days"].astype(int)

    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df[CLEAN_COLUMNS]
