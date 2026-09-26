from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 10
QUESTION_PLAN = ["summary", "authors", "date", "categories", "summary", "authors", "date", "categories", "summary", "authors"]


def _question_for(question_type: str, row: pd.Series) -> tuple[str, str]:
    title = row["title"]
    if question_type == "summary":
        return f"What is the main contribution of '{title}'?", first_sentence(row["summary"])
    if question_type == "authors":
        return f"Who authored '{title}'?", row["authors_joined"]
    if question_type == "date":
        return f"When was '{title}' published?", str(row["published"])
    if question_type == "categories":
        return f"What categories does '{title}' belong to?", row["categories_joined"]
    raise ValueError(f"Unknown question type: {question_type}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} clean documents to build the test set, got {len(df)}.")

    ordered = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    step = len(ordered) / len(QUESTION_PLAN)
    picked = ordered.iloc[[int(i * step) for i in range(len(QUESTION_PLAN))]]

    test_set: list[dict[str, Any]] = []
    for number, (question_type, (_, row)) in enumerate(zip(QUESTION_PLAN, picked.iterrows(), strict=True), start=1):
        question, ground_truth = _question_for(question_type, row)
        test_set.append(
            {
                "id": f"q{number:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    write_json(output_path, test_set)
    return test_set
