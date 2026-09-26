from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("GX_ANALYTICS_ENABLED", "False")

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

MIN_ROWS = 20
MAX_ROWS = 30
MIN_TITLE_CHARS = 8
MIN_SUMMARY_CHARS = 50
MAX_STALE_RATIO = 0.25


def _build_suite(suite_name: str) -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name=suite_name)
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_ROWS, max_value=MAX_ROWS))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=MIN_TITLE_CHARS)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS)
    )
    return suite


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)):
        return value
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _summarize_result(result) -> dict[str, Any]:
    config = result.expectation_config
    details = result.result or {}
    return {
        "expectation": config.type,
        "column": config.kwargs.get("column"),
        "success": bool(result.success),
        "observed_value": _plain(details.get("observed_value")),
        "unexpected_count": _plain(details.get("unexpected_count")),
        "unexpected_percent": _plain(details.get("unexpected_percent")),
    }


def _freshness_summary(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    published = pd.to_datetime(df["published"], errors="coerce")
    total_rows = int(len(df))
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    return {
        "latest_published": published.max().strftime("%Y-%m-%d") if published.notna().any() else None,
        "oldest_published": published.min().strftime("%Y-%m-%d") if published.notna().any() else None,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": MAX_STALE_RATIO,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": total_rows > 0 and stale_ratio <= MAX_STALE_RATIO,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(_build_suite(f"papers_{report_name}_suite"))
    validation = batch.validate(suite)

    expectations = [_summarize_result(result) for result in validation.results]
    freshness = _freshness_summary(df, settings)
    report = {
        "report_name": report_name,
        "checked_at": now_utc().isoformat(),
        "row_count": int(len(df)),
        "gx_version": gx.__version__,
        "gx_success": bool(validation.success),
        "failed_expectations": [item for item in expectations if not item["success"]],
        "expectations": expectations,
        "freshness": freshness,
        "success": bool(validation.success) and freshness["is_fresh"],
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    payload = {"checked_at": now_utc().isoformat(), **_freshness_summary(df, settings)}
    write_json(report_path, payload)
    return payload
