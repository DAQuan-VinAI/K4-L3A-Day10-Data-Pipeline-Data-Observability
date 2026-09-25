from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import comparison_rows, generate_corruption_report
from pipelines.phase1 import save_clean_artifacts
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatePaths:
    name: str
    clean_csv: Path
    clean_json: Path
    embeddings_json: Path
    metrics: Path
    answers: Path
    freshness: Path


@dataclass(frozen=True)
class StateResult:
    evaluation: EvaluationBundle
    quality: dict[str, Any]
    freshness: dict[str, Any]


def state_paths(settings: Settings, name: str) -> StatePaths:
    paths = settings.paths
    if name == "corrupted":
        return StatePaths(
            name, paths.corrupted_clean_csv, paths.corrupted_clean_json, paths.corrupted_embeddings_json,
            paths.corrupted_metrics, paths.corrupted_answers, paths.quality_dir / "corrupted_freshness_report.json",
        )
    if name == "repaired":
        return StatePaths(
            name, paths.repaired_clean_csv, paths.repaired_clean_json, paths.repaired_embeddings_json,
            paths.repaired_metrics, paths.repaired_answers, paths.quality_dir / "repaired_freshness_report.json",
        )
    raise ValueError(f"Unknown state: {name}")


def evaluate_state(df: pd.DataFrame, settings: Settings, name: str) -> StateResult:
    """Luu artifacts, chay quality gate (chi ghi nhan, khong chan) roi index + evaluate cho 1 trang thai du lieu.

    Quality gate khong chan o day: muc dich la do xem RAG suy giam the nao neu du lieu ban lot qua.
    """
    target = state_paths(settings, name)
    save_clean_artifacts(df, target.clean_csv, target.clean_json)
    quality = run_data_quality_checks(df, settings, name)
    freshness = build_freshness_report(df, settings, target.freshness)
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=target.embeddings_json)
    evaluation = evaluate_pipeline(settings, index, settings.paths.eval_testset, target.metrics, target.answers)
    logger.info(
        "[%s] quality=%s fresh=%s hit_rate=%.2f token_f1=%.2f judge=%.2f",
        name,
        quality["success"],
        freshness["is_fresh"],
        evaluation.summary["retrieval_hit_rate"],
        evaluation.summary["mean_token_f1"],
        evaluation.summary["judge_accuracy"],
    )
    return StateResult(evaluation=evaluation, quality=quality, freshness=freshness)


def repair_from_raw(settings: Settings) -> pd.DataFrame:
    """Idempotent repair: bo qua du lieu da hong, tai tao tu raw records (nguon su that) bang dung ham cleaning.

    Chay lai bao nhieu lan cung ra cung ket qua vi chi phu thuoc vao raw snapshot, khong vao trang thai hong.
    """
    records = load_raw_records(settings.paths.raw_records_json)
    return build_clean_dataframe(records, now_utc())


def _print_comparison(rows: list[tuple[str, str, str, str]]) -> None:
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    for position, row in enumerate(rows):
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))
        if position == 0:
            print("  ".join("-" * width for width in widths))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "sentence_transformers", "great_expectations"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = load_settings()
    paths = settings.paths
    if not (paths.baseline_metrics.exists() and paths.clean_json.exists() and paths.eval_testset.exists()):
        raise RuntimeError("Thieu baseline artifacts. Hay chay `python script/run_phase1.py` truoc.")

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_quality = read_json(paths.baseline_quality_report)
    baseline_freshness = read_json(paths.freshness_report)
    clean_df = pd.read_json(paths.clean_json)
    logger.info("[1/4] Nap baseline: %d dong", len(clean_df))

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    logger.info("[2/4] Tiem 6 kich ban loi -> %d dong (log: %s)", len(corrupted_df), paths.corruption_log)
    corrupted = evaluate_state(corrupted_df, settings, "corrupted")

    repaired_df = repair_from_raw(settings)
    same_ids = set(repaired_df["paper_id"]) == set(clean_df["paper_id"])
    logger.info("[3/4] Repair tu raw -> %d dong, khop baseline paper_id: %s", len(repaired_df), same_ids)
    repaired = evaluate_state(repaired_df, settings, "repaired")

    corruption_log = read_json(paths.corruption_log)
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted.evaluation.summary,
        repaired.evaluation.summary,
        corrupted.quality,
        repaired.quality,
        corrupted.freshness,
        repaired.freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
        corruption_log=corruption_log,
        corrupted_answers=corrupted.evaluation.answers,
    )
    logger.info("[4/4] Bao cao -> %s", paths.comparison_report)

    states = {
        "Baseline": (baseline_metrics, baseline_quality, baseline_freshness),
        "Corrupted": (corrupted.evaluation.summary, corrupted.quality, corrupted.freshness),
        "Repaired": (repaired.evaluation.summary, repaired.quality, repaired.freshness),
    }
    print()
    _print_comparison(comparison_rows(states))
