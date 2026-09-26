from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text

METRIC_LABELS = [
    ("retrieval_hit_rate", "Retrieval Hit Rate"),
    ("mean_token_f1", "Mean Token F1"),
    ("judge_accuracy", "Judge Accuracy"),
    ("mean_judge_score", "Mean Judge Score (1-5)"),
]


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    return "-" if value is None else str(value)


def _quality_lines(quality: dict[str, Any]) -> list[str]:
    lines = [
        "| Expectation | Column | Result | Unexpected |",
        "|---|---|---|---|",
    ]
    for item in quality.get("expectations", []):
        unexpected = item.get("unexpected_count")
        if unexpected is None:
            unexpected = f"observed={item.get('observed_value')}"
        lines.append(
            f"| `{item['expectation']}` | {item.get('column') or '(table)'} | {_fmt(item['success'])} | {unexpected} |"
        )
    return lines


def _freshness_lines(freshness: dict[str, Any]) -> list[str]:
    return [
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        f"- Stale rows (age_days > {freshness.get('threshold_days')}): "
        f"{freshness.get('stale_rows')}/{freshness.get('total_rows')} ({freshness.get('stale_ratio', 0):.1%})",
        f"- SLA: at most {freshness.get('max_stale_ratio', 0):.0%} stale rows -> **{_fmt(freshness.get('is_fresh'))}**",
    ]


def format_comparison_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
) -> str:
    lines = [
        "| Metric | Baseline | Corrupted | Repaired | Corrupted vs Baseline | Repaired vs Baseline |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, label in METRIC_LABELS:
        base, bad, fixed = (m.get(key) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))
        lines.append(
            f"| {label} | {_fmt(base)} | {_fmt(bad)} | {_fmt(fixed)} | {bad - base:+.4f} | {fixed - base:+.4f} |"
        )
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = [
        "# Phase 1 Report - Baseline Pipeline",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## 1. Source",
        "",
    ]
    lines += [f"- {key.replace('_', ' ').capitalize()}: {value}" for key, value in source_summary.items()]
    lines += [
        "",
        "## 2. Baseline Evaluation",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Samples | {metrics.get('samples')} |",
    ]
    lines += [f"| {label} | {_fmt(metrics.get(key))} |" for key, label in METRIC_LABELS]
    lines += [
        "",
        "## 3. Data Quality Gate (Great Expectations 1.x)",
        "",
        f"- Rows checked: {quality.get('row_count')}",
        f"- GX suite result: **{_fmt(quality.get('gx_success'))}**",
        f"- Overall gate (GX + freshness): **{_fmt(quality.get('success'))}**",
        "",
    ]
    lines += _quality_lines(quality)
    lines += ["", "## 4. Freshness SLA", ""]
    lines += _freshness_lines(freshness)
    write_text(report_path, "\n".join(lines) + "\n")


def _analysis_lines(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
) -> list[str]:
    lines = []
    for key, label in METRIC_LABELS:
        base, bad, fixed = (m.get(key, 0.0) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))
        recovered = "fully recovered" if abs(fixed - base) < 1e-9 else f"recovered to {fixed:.4f}"
        lines.append(f"- **{label}** went from {base:.4f} to {bad:.4f} on corrupted data, then {recovered} after repair.")

    failed = corrupted_quality.get("failed_expectations", [])
    if failed:
        names = ", ".join(f"`{item['expectation']}`({item.get('column') or 'table'})" for item in failed)
        lines.append(f"- The quality gate caught the corruption: {len(failed)} expectations failed ({names}).")
    else:
        lines.append("- The GX suite did not flag the corrupted batch; the expectations need to be tightened.")
    if not corrupted_quality.get("freshness", {}).get("is_fresh", True):
        lines.append("- The freshness SLA also failed on the corrupted batch because of the backdated publication dates.")
    lines.append(
        f"- After repairing from the raw snapshot the gate is **{_fmt(repaired_quality.get('success'))}**, "
        "so the repaired collection is safe to serve again."
    )
    return lines


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    lines = [
        "# Corruption Report - Baseline vs Corrupted vs Repaired",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## 1. RAG Metrics",
        "",
        format_comparison_table(baseline_metrics, corrupted_metrics, repaired_metrics),
        "",
        "## 2. Data Quality Gate",
        "",
        "| State | Rows | GX suite | Freshness | Overall gate |",
        "|---|---:|---|---|---|",
    ]
    for state, quality in (("Corrupted", corrupted_quality), ("Repaired", repaired_quality)):
        lines.append(
            f"| {state} | {quality.get('row_count')} | {_fmt(quality.get('gx_success'))} | "
            f"{_fmt(quality.get('freshness', {}).get('is_fresh'))} | {_fmt(quality.get('success'))} |"
        )
    lines += ["", "### Corrupted batch expectations", ""]
    lines += _quality_lines(corrupted_quality)
    lines += ["", "### Repaired batch expectations", ""]
    lines += _quality_lines(repaired_quality)
    lines += ["", "## 3. Freshness SLA", "", "**Corrupted**", ""]
    lines += _freshness_lines(corrupted_freshness)
    lines += ["", "**Repaired**", ""]
    lines += _freshness_lines(repaired_freshness)
    lines += ["", "## 4. Analysis", ""]
    lines += _analysis_lines(baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality)
    write_text(report_path, "\n".join(lines) + "\n")
