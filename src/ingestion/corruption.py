from __future__ import annotations

import numpy as np
import pandas as pd

from core.utils import compact_join, now_utc, write_json
from ingestion.cleaning import build_text_for_embedding

SEED = 42
DROP_LATEST = 3
BLANK_SUMMARY = 4
NOISY_SUMMARY = 4
TRUNCATED_TITLE = 5
STALE_DATE = 7
DUPLICATE_ROWS = 2
STALE_SHIFT_DAYS = 3 * 365
NOISE_TOKENS = ["#@!", "lorem", "~~", "NaN", "???", "<br/>", "%%%", "ipsum", "0xDEAD"]


def _pick(rng: np.random.Generator, candidates: list[int], size: int) -> list[int]:
    size = min(size, len(candidates))
    return sorted(int(i) for i in rng.choice(candidates, size=size, replace=False))


def _inject_noise(text: str, rng: np.random.Generator) -> str:
    words = text.split()
    for _ in range(max(3, len(words) // 3)):
        position = int(rng.integers(0, len(words) + 1))
        words.insert(position, str(rng.choice(NOISE_TOKENS)))
    return " ".join(words)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    corrupted = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True).copy()
    log: list[dict] = []

    def record(kind: str, description: str, rows: list[int]) -> None:
        log.append(
            {
                "type": kind,
                "description": description,
                "affected_rows": len(rows),
                "affected_paper_ids": corrupted.loc[rows, "paper_id"].tolist(),
            }
        )

    latest = list(range(min(DROP_LATEST, len(corrupted))))
    record("drop_latest_records", f"Dropped the {len(latest)} most recently published papers.", latest)
    corrupted = corrupted.drop(index=latest).reset_index(drop=True)

    all_rows = list(corrupted.index)
    blank_rows = _pick(rng, all_rows, BLANK_SUMMARY)
    record("blank_summary", "Replaced the abstract with an empty string.", blank_rows)
    corrupted.loc[blank_rows, "summary"] = ""

    noisy_rows = _pick(rng, [i for i in all_rows if i not in blank_rows], NOISY_SUMMARY)
    record("inject_noise", "Inserted junk tokens into the abstract.", noisy_rows)
    for row in noisy_rows:
        corrupted.at[row, "summary"] = _inject_noise(corrupted.at[row, "summary"], rng)

    truncated_rows = _pick(rng, all_rows, TRUNCATED_TITLE)
    record("truncate_title", "Cut the title down to its first 6 characters.", truncated_rows)
    corrupted.loc[truncated_rows, "title"] = corrupted.loc[truncated_rows, "title"].str[:6]

    stale_rows = _pick(rng, all_rows, STALE_DATE)
    record("stale_date", f"Moved the publication date back {STALE_SHIFT_DAYS} days.", stale_rows)
    shifted = pd.to_datetime(corrupted.loc[stale_rows, "published"]) - pd.Timedelta(days=STALE_SHIFT_DAYS)
    corrupted.loc[stale_rows, "published"] = shifted.dt.strftime("%Y-%m-%d")
    corrupted.loc[stale_rows, "age_days"] = corrupted.loc[stale_rows, "age_days"].astype(int) + STALE_SHIFT_DAYS

    duplicate_rows = _pick(rng, all_rows, DUPLICATE_ROWS)
    record("duplicate_rows", "Appended exact copies of existing rows.", duplicate_rows)
    corrupted = pd.concat([corrupted, corrupted.loc[duplicate_rows]], ignore_index=True)

    corrupted["authors_joined"] = corrupted["authors"].apply(compact_join)
    corrupted["categories_joined"] = corrupted["categories"].apply(compact_join)
    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = corrupted.apply(build_text_for_embedding, axis=1)

    write_json(
        output_log_path,
        {
            "created_at": now_utc().isoformat(),
            "seed": SEED,
            "input_rows": int(len(df)),
            "output_rows": int(len(corrupted)),
            "corruptions": log,
        },
    )
    return corrupted
