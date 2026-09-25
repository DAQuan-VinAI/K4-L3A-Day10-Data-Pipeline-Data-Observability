from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)

DEMO_QUESTION_COUNT = 2


def save_clean_artifacts(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def _load_records(settings: Settings):
    # Uu tien ban raw da luu (lineage); chi goi API khi chua co hoac REFRESH_SOURCE=1.
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        return load_raw_records(settings.paths.raw_records_json)
    return fetch_source_records(settings)


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict]) -> None:
    from retrieval.agent import build_agent, run_agent_question

    try:
        agent = build_agent(settings, index)
        answers = [
            {"question": item["question"], "answer": run_agent_question(agent, item["question"])}
            for item in test_set[:DEMO_QUESTION_COUNT]
        ]
    except Exception as exc:  # Agent demo la tuy chon, khong duoc lam hong baseline.
        logger.warning("Bo qua agent demo: %s", exc)
        answers = [{"error": str(exc)}]
    write_json(settings.paths.demo_answers, answers)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for noisy in ("httpx", "sentence_transformers", "great_expectations"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = load_settings()
    paths = settings.paths

    records = _load_records(settings)
    logger.info("[1/6] Nap %d raw records", len(records))

    clean_df = build_clean_dataframe(records, now_utc())
    save_clean_artifacts(clean_df, paths.clean_csv, paths.clean_json)
    logger.info("[2/6] Clean %d dong -> %s", len(clean_df), paths.clean_csv)

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)
    logger.info("[3/6] Quality gate success=%s, is_fresh=%s", quality["success"], freshness["is_fresh"])
    if not quality["success"]:
        raise RuntimeError(f"Quality gate that bai, dung pipeline. Xem {paths.baseline_quality_report}")

    index = LocalEmbeddingIndex.build(clean_df, settings, embeddings_output_path=paths.embeddings_json)
    logger.info("[4/6] Chroma collection %s: %d docs", index.collection_name, index.collection.count())

    test_set = load_or_create_test_set(clean_df, paths.eval_testset, refresh=settings.refresh_test_set)
    bundle = evaluate_pipeline(settings, index, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers)
    logger.info(
        "[5/6] Hit rate=%.2f, token F1=%.2f, judge accuracy=%.2f",
        bundle.summary["retrieval_hit_rate"],
        bundle.summary["mean_token_f1"],
        bundle.summary["judge_accuracy"],
    )

    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": int(len(clean_df)),
        "collection_name": index.collection_name,
        "embedding_model": settings.embedding_model,
        "llm": f"{settings.llm_provider}/{settings.model_name}",
        "test_set_size": len(test_set),
        "answers": bundle.answers,
    }
    generate_phase1_report(paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    _run_agent_demo(settings, index, test_set)
    logger.info("[6/6] Bao cao -> %s", paths.baseline_report)
