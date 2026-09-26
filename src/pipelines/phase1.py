from __future__ import annotations

import json

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

DEMO_QUESTIONS = 2


def save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, json.loads(df.to_json(orient="records", force_ascii=False)))


def _run_agent_demo(settings, index, test_set: list[dict]) -> None:
    questions = [item["question"] for item in test_set[:DEMO_QUESTIONS]]
    try:
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings, index)
        answers = [{"question": q, "answer": run_agent_question(agent, q)} for q in questions]
    except Exception as exc:
        print(f"[phase1] Agent demo skipped: {exc}")
        answers = [{"question": q, "answer": None, "error": str(exc)} for q in questions]
    write_json(settings.paths.demo_answers, answers)


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    records = fetch_source_records(settings)
    print(f"[phase1] Loaded {len(records)} raw records.")

    df = build_clean_dataframe(records, run_date)
    save_dataframe(df, settings.paths.clean_csv, settings.paths.clean_json)
    print(f"[phase1] Clean dataframe: {len(df)} rows.")

    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"[phase1] Indexed {len(index.documents)} documents into '{index.collection_name}'.")

    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
    print(f"[phase1] Test set: {len(test_set)} questions.")

    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    metrics = bundle.summary

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": len(df),
        "run_date": run_date.date().isoformat(),
        "embedding_model": settings.embedding_model,
        "collection": index.collection_name,
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, metrics, quality, freshness)

    _run_agent_demo(settings, index, test_set)

    print(
        f"[phase1] Baseline hit_rate={metrics['retrieval_hit_rate']:.4f} "
        f"token_f1={metrics['mean_token_f1']:.4f} judge_accuracy={metrics['judge_accuracy']:.4f}"
    )
    print(f"[phase1] Quality gate success={quality['success']} fresh={freshness['is_fresh']}")
    print(f"[phase1] Report written to {settings.paths.baseline_report}")
