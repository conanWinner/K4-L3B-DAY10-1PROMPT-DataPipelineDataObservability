from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import format_comparison_table, generate_corruption_report
from pipelines.phase1 import save_dataframe
from retrieval.index import LocalEmbeddingIndex


def _evaluate(settings, df: pd.DataFrame, embeddings_path, metrics_path, answers_path) -> dict:
    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    print(f"[corruption] Indexed {len(index.documents)} documents into '{index.collection_name}'.")
    return evaluate_pipeline(settings, index, settings.paths.eval_testset, metrics_path, answers_path).summary


def main() -> None:
    settings = load_settings()
    paths = settings.paths
    for required in (paths.baseline_metrics, paths.clean_json, paths.eval_testset, paths.raw_records_json):
        if not required.exists():
            raise SystemExit(f"Missing {required}. Run `python script/run_phase1.py` first.")

    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.read_json(paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    print(f"[corruption] Corrupted dataframe: {len(corrupted_df)} rows (log: {paths.corruption_log.name}).")

    corrupted_metrics = _evaluate(
        settings, corrupted_df, paths.corrupted_embeddings_json, paths.corrupted_metrics, paths.corrupted_answers
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"[corruption] Corrupted quality gate success={corrupted_quality['success']}")

    repaired_df = build_clean_dataframe(load_raw_records(paths.raw_records_json), now_utc())
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    if not repaired_quality["success"]:
        raise SystemExit("Repaired data failed the quality gate; refusing to serve it.")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )
    save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    print(f"[corruption] Repaired dataframe: {len(repaired_df)} rows, quality gate passed.")

    repaired_metrics = _evaluate(
        settings, repaired_df, paths.repaired_embeddings_json, paths.repaired_metrics, paths.repaired_answers
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print()
    print(format_comparison_table(baseline_metrics, corrupted_metrics, repaired_metrics))
    print()
    print(f"[corruption] Report written to {paths.comparison_report}")
