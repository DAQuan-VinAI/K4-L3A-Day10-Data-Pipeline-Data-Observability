from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

MIN_ROWS = 5
MAX_ROWS = 5000
MIN_SUMMARY_CHARS = 30
REQUIRED_COLUMNS = ("paper_id", "title", "text_for_embedding")
MAX_STALE_RATIO = 0.25


def build_expectations() -> list[gx.expectations.Expectation]:
    return [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_ROWS, max_value=MAX_ROWS),
        *[gx.expectations.ExpectColumnValuesToNotBeNull(column=column) for column in REQUIRED_COLUMNS],
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS),
    ]


def _validate_with_gx(df: pd.DataFrame, suite_name: str):
    # GX 1.x: ephemeral context chay tren RAM, khong sinh file cau hinh.
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    for expectation in build_expectations():
        suite.add_expectation(expectation)
    return batch.validate(suite)


def _summarize_result(result) -> dict[str, Any]:
    kwargs = result.expectation_config.kwargs
    details = result.result or {}
    return {
        "expectation": result.expectation_config.type,
        "column": kwargs.get("column"),
        "success": bool(result.success),
        "observed_value": details.get("observed_value"),
        "unexpected_count": details.get("unexpected_count"),
        "partial_unexpected_list": [str(value)[:120] for value in details.get("partial_unexpected_list", [])],
    }


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = int(len(df))
    if total_rows == 0 or "age_days" not in df.columns:
        stale_rows = 0
        latest = oldest = None
    else:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages > settings.freshness_threshold_days).sum())
        published = pd.to_datetime(df["published"], errors="coerce")
        latest = published.max().date().isoformat() if published.notna().any() else None
        oldest = published.min().date().isoformat() if published.notna().any() else None
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    return {
        "checked_at": now_utc().isoformat(),
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": MAX_STALE_RATIO,
        "is_fresh": total_rows > 0 and stale_ratio <= MAX_STALE_RATIO,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    validation = _validate_with_gx(df, suite_name=f"{report_name}_papers_suite")
    statistics = validation.statistics
    report = {
        "report_name": report_name,
        "checked_at": now_utc().isoformat(),
        "engine": f"great_expectations {gx.__version__}",
        "success": bool(validation.success),
        "row_count": int(len(df)),
        "statistics": {
            "evaluated_expectations": int(statistics["evaluated_expectations"]),
            "successful_expectations": int(statistics["successful_expectations"]),
            "unsuccessful_expectations": int(statistics["unsuccessful_expectations"]),
            "success_percent": statistics["success_percent"],
        },
        "expectations": [_summarize_result(result) for result in validation.results],
        "freshness": _freshness_payload(df, settings),
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    payload = _freshness_payload(df, settings)
    write_json(report_path, payload)
    return payload
