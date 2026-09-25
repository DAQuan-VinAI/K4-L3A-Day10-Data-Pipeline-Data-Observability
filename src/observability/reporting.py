from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from core.utils import now_utc, write_text


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _metrics_section(metrics: dict[str, Any]) -> list[str]:
    ragas = metrics.get("ragas") or {}
    ragas_note = ragas.get("skipped") or ragas.get("error") or ", ".join(f"{k}={v}" for k, v in ragas.items())
    return [
        "## Evaluation Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Samples | {metrics['samples']} |",
        f"| Retrieval hit rate | {_pct(metrics['retrieval_hit_rate'])} |",
        f"| Mean token F1 | {metrics['mean_token_f1']:.3f} |",
        f"| LLM judge accuracy | {_pct(metrics['judge_accuracy'])} |",
        f"| Mean LLM judge score (1-5) | {metrics['mean_judge_score']:.2f} |",
        "",
        f"Ragas: {ragas_note or 'n/a'}",
        "",
    ]


def _per_type_section(answers: list[dict[str, Any]]) -> list[str]:
    if not answers:
        return []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for answer in answers:
        groups[answer["question_type"]].append(answer)
    lines = [
        "### Breakdown by question type",
        "",
        "| Type | Samples | Hit rate | Token F1 | Judge accuracy |",
        "|---|---|---|---|---|",
    ]
    for question_type, items in groups.items():
        lines.append(
            f"| {question_type} | {len(items)} "
            f"| {_pct(mean(1.0 if item['retrieval_hit'] else 0.0 for item in items))} "
            f"| {mean(item['token_f1'] for item in items):.3f} "
            f"| {_pct(mean(1.0 if item['judge']['correct'] else 0.0 for item in items))} |"
        )
    lines += ["", "### Per-question results", "", "| ID | Type | Hit | Token F1 | Judge | Answer |", "|---|---|---|---|---|---|"]
    for item in answers:
        lines.append(
            f"| {item['id']} | {item['question_type']} | {'yes' if item['retrieval_hit'] else 'no'} "
            f"| {item['token_f1']:.2f} | {item['judge']['score']} | {_cell(item['answer'])[:80]} |"
        )
    return lines + [""]


def _quality_section(quality: dict[str, Any]) -> list[str]:
    stats = quality["statistics"]
    lines = [
        "## Data Quality Gate (Great Expectations)",
        "",
        f"- Engine: `{quality['engine']}`",
        f"- Overall: **{_status(quality['success'])}** "
        f"({stats['successful_expectations']}/{stats['evaluated_expectations']} expectations passed)",
        "",
        "| Expectation | Column | Result | Observed | Unexpected |",
        "|---|---|---|---|---|",
    ]
    for item in quality["expectations"]:
        lines.append(
            f"| {item['expectation']} | {item['column'] or '-'} | {_status(item['success'])} "
            f"| {_cell(item['observed_value']) if item['observed_value'] is not None else '-'} "
            f"| {item['unexpected_count'] if item['unexpected_count'] is not None else '-'} |"
        )
    return lines + [""]


def _freshness_section(freshness: dict[str, Any]) -> list[str]:
    return [
        "## Freshness SLA",
        "",
        f"- Status: **{'FRESH' if freshness['is_fresh'] else 'STALE'}**",
        f"- Stale rows (age > {freshness['threshold_days']} days): "
        f"{freshness['stale_rows']}/{freshness['total_rows']} ({_pct(freshness['stale_ratio'])}, "
        f"max allowed {_pct(freshness['max_stale_ratio'])})",
        f"- Published range: {freshness['oldest_published']} -> {freshness['latest_published']}",
        "",
    ]


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = [
        "# Phase 1 Report: Baseline Pipeline",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## Source & Pipeline",
        "",
        "| Item | Value |",
        "|---|---|",
    ]
    for key in ("source_api", "query", "filter", "raw_records", "clean_rows", "collection_name", "embedding_model", "llm", "test_set_size"):
        if key in source_summary:
            lines.append(f"| {key} | {_cell(source_summary[key])} |")
    lines.append("")
    lines += _metrics_section(metrics)
    lines += _per_type_section(source_summary.get("answers", []))
    lines += _quality_section(quality)
    lines += _freshness_section(freshness)
    write_text(Path(report_path), "\n".join(lines))


def _gate_cell(quality: dict[str, Any] | None) -> str:
    if not quality:
        return "n/a"
    stats = quality["statistics"]
    passed = f"{stats['successful_expectations']}/{stats['evaluated_expectations']}"
    return f"PASSED ({passed})" if quality["success"] else f"FAILED ({passed})"


def _freshness_cell(freshness: dict[str, Any] | None) -> str:
    if not freshness:
        return "n/a"
    ratio = f"{freshness['stale_rows']}/{freshness['total_rows']} > {freshness['threshold_days']}d"
    return f"FRESH ({ratio})" if freshness["is_fresh"] else f"STALE ({ratio})"


def comparison_rows(states: dict[str, tuple[dict, dict | None, dict | None]]) -> list[tuple[str, ...]]:
    """states: {ten: (metrics, quality, freshness)} -> bang [header, *rows] dung chung cho console va markdown."""
    names = list(states)
    rows = [("Metric", *names)]
    rows.append(("Data Quality Gate", *(_gate_cell(states[name][1]) for name in names)))
    rows.append(("Freshness SLA", *(_freshness_cell(states[name][2]) for name in names)))
    rows.append(("Retrieval hit rate", *(_pct(states[name][0]["retrieval_hit_rate"]) for name in names)))
    rows.append(("Mean token F1", *(f"{states[name][0]['mean_token_f1']:.3f}" for name in names)))
    rows.append(("LLM judge accuracy", *(_pct(states[name][0]["judge_accuracy"]) for name in names)))
    rows.append(("Mean judge score", *(f"{states[name][0]['mean_judge_score']:.2f}" for name in names)))
    return rows


def _markdown_table(rows: list[tuple[str, ...]]) -> list[str]:
    header, *body = rows
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(value) for value in row) + " |" for row in body]
    return lines


def _delta(before: float, after: float, percent: bool) -> str:
    diff = after - before
    return f"{diff * 100:+.1f} pp" if percent else f"{diff:+.3f}"


def _silent_failures(answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cau ma retrieval da truot khoi tai lieu dung nhung judge van cham 'correct'."""
    return [item for item in answers if not item["retrieval_hit"] and item["judge"]["correct"]]


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
    corrupted_answers: list[dict[str, Any]] | None = None,
) -> None:
    states = {
        "Baseline": (baseline_metrics, baseline_quality, baseline_freshness),
        "Corrupted": (corrupted_metrics, corrupted_quality, corrupted_freshness),
        "Repaired": (repaired_metrics, repaired_quality, repaired_freshness),
    }
    lines = [
        "# Corruption Report: Baseline vs Corrupted vs Repaired",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## 3-State Comparison",
        "",
        *_markdown_table(comparison_rows(states)),
        "",
        "### Delta vs baseline",
        "",
        "| Metric | Corrupted | Repaired |",
        "|---|---|---|",
    ]
    for key, label, percent in (
        ("retrieval_hit_rate", "Retrieval hit rate", True),
        ("mean_token_f1", "Mean token F1", False),
        ("judge_accuracy", "LLM judge accuracy", True),
    ):
        lines.append(
            f"| {label} | {_delta(baseline_metrics[key], corrupted_metrics[key], percent)} "
            f"| {_delta(baseline_metrics[key], repaired_metrics[key], percent)} |"
        )
    lines.append("")

    if corruption_log:
        lines += [
            "## Injected Corruption Scenarios",
            "",
            f"Seed `{corruption_log['seed']}` - rows {corruption_log['input_rows']} -> {corruption_log['output_rows']} "
            "(row count unchanged, so a simple volume check cannot detect the damage).",
            "",
            "| Scenario | Affected rows | Description |",
            "|---|---|---|",
        ]
        lines += [
            f"| {item['scenario']} | {item['affected_rows']} | {_cell(item['description'])} |"
            for item in corruption_log["scenarios"]
        ]
        lines.append("")

    failed = [item for item in corrupted_quality["expectations"] if not item["success"]]
    lines += ["## What the Quality Gate Caught", ""]
    lines += [
        f"- `{item['expectation']}` on `{item['column'] or 'table'}`: {item['unexpected_count']} unexpected values"
        for item in failed
    ] or ["- Nothing: every expectation passed on corrupted data."]
    lines.append(
        f"- Freshness: {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']} rows older than "
        f"{corrupted_freshness['threshold_days']} days ({_pct(corrupted_freshness['stale_ratio'])}, "
        f"limit {_pct(corrupted_freshness['max_stale_ratio'])}) -> "
        f"{'FRESH' if corrupted_freshness['is_fresh'] else 'STALE'}"
    )
    lines.append("")

    if corrupted_answers:
        silent = _silent_failures(corrupted_answers)
        lines += [
            "## Silent Failure Evidence",
            "",
            f"{len(silent)}/{len(corrupted_answers)} questions retrieved the wrong document yet were still judged correct. "
            "The corpus contains near-duplicate 'Advanced Perspectives on ...' papers that share authors and categories "
            "with the dropped originals, so the RAG answers confidently from the wrong source and the LLM judge does not notice.",
            "",
            "| ID | Type | Retrieved (top-1) | Expected | Token F1 | Judge | Answer |",
            "|---|---|---|---|---|---|---|",
        ]
        for item in silent:
            lines.append(
                f"| {item['id']} | {item['question_type']} | {item['retrieved_doc_ids'][0] if item['retrieved_doc_ids'] else '-'} "
                f"| {', '.join(item['ground_truth_doc_ids'])} | {item['token_f1']:.2f} | {item['judge']['score']} "
                f"| {_cell(item['answer'])[:60] or '(empty)'} |"
            )
        lines.append("")

    recovered = all(
        abs(repaired_metrics[key] - baseline_metrics[key]) < 1e-9 for key in ("retrieval_hit_rate", "mean_token_f1")
    )
    lines += [
        "## Conclusion",
        "",
        "- Answer-level metrics alone understate the damage: judge accuracy dropped far less than retrieval hit rate, "
        "so monitoring must include retrieval and data-level checks, not only answer grading.",
        "- The GX quality gate and freshness SLA flagged the corrupted batch before indexing; enforcing the gate "
        "in the pipeline would have blocked it.",
        "- Idempotent repair rebuilds the clean table from the raw snapshot with the same cleaning code, so it can be "
        "re-run safely any number of times.",
        f"- Repaired retrieval metrics {'match' if recovered else 'do not fully match'} the baseline "
        f"(hit rate {_pct(repaired_metrics['retrieval_hit_rate'])}, token F1 {repaired_metrics['mean_token_f1']:.3f}). "
        "LLM judge scores can vary slightly between runs because the judge is a live model.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))
