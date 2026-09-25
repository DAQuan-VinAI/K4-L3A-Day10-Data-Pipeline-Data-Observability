from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json

MIN_DOCUMENTS = 5
QUESTIONS_PER_TYPE = 2
QUESTION_TYPES = ("summary", "authors", "date", "category", "multi_hop")


class TestSet(list):
    """List cac cau hoi, kem thuoc tinh `.samples` cho lenh kiem tra CP2."""

    @property
    def samples(self) -> list[dict[str, Any]]:
        return list(self)


def _pick_papers(df: pd.DataFrame, count: int) -> list[dict[str, Any]]:
    """Chon paper dai dien, deterministic: uu tien ban goc (khong phai 'Advanced Perspectives'),
    du authors/categories, va title khong chua dau nhay don (qa.py dung '...' de khop title)."""
    candidates = df[
        (df["authors_joined"].fillna("") != "")
        & (df["categories_joined"].fillna("") != "")
        & ~df["title"].str.contains("'", regex=False)
    ].copy()
    candidates["is_derivative"] = candidates["title"].str.startswith("Advanced Perspectives")
    candidates = candidates.sort_values(["is_derivative", "published", "paper_id"], ascending=[True, False, True])
    return candidates.head(count).to_dict(orient="records")


def _item(index: int, question_type: str, question: str, ground_truth: str, doc_ids: list[str]) -> dict[str, Any]:
    return {
        "id": f"q{index:02d}",
        "type": question_type,
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": doc_ids,
    }


def _build_question(question_type: str, papers: list[dict[str, Any]]) -> tuple[str, str, list[str]]:
    first = papers[0]
    if question_type == "summary":
        return (
            f"What is the main finding of the paper '{first['title']}'?",
            first_sentence(first["summary"]),
            [first["paper_id"]],
        )
    if question_type == "authors":
        return (f"Who authored the paper '{first['title']}'?", first["authors_joined"], [first["paper_id"]])
    if question_type == "date":
        return (f"When was the paper '{first['title']}' published?", first["published"], [first["paper_id"]])
    if question_type == "category":
        return (
            f"What categories does the paper '{first['title']}' belong to?",
            first["categories_joined"],
            [first["paper_id"]],
        )
    second = papers[1]
    return (
        f"Who authored the paper '{first['title']}', and when was the paper '{second['title']}' published?",
        f"{first['authors_joined']}; {second['published']}",
        [first["paper_id"], second["paper_id"]],
    )


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Sinh benchmark test set: QUESTIONS_PER_TYPE cau cho moi loai trong QUESTION_TYPES."""
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Can it nhat {MIN_DOCUMENTS} document de sinh test set, hien co {len(df)}")

    # Moi cau single-hop dung 1 paper, multi_hop dung 2 paper -> khong paper nao bi hoi lap lai.
    papers_needed = QUESTIONS_PER_TYPE * (len(QUESTION_TYPES) + 1)
    papers = _pick_papers(df, papers_needed)
    if len(papers) < papers_needed:
        raise ValueError(f"Can {papers_needed} paper hop le de sinh test set, chi co {len(papers)}")

    test_set: list[dict[str, Any]] = []
    cursor = 0
    for question_type in QUESTION_TYPES:
        for _ in range(QUESTIONS_PER_TYPE):
            width = 2 if question_type == "multi_hop" else 1
            question, ground_truth, doc_ids = _build_question(question_type, papers[cursor : cursor + width])
            cursor += width
            test_set.append(_item(len(test_set) + 1, question_type, question, ground_truth, doc_ids))

    write_json(Path(output_path), test_set)
    return test_set


def load_or_create_test_set(df: pd.DataFrame, output_path, refresh: bool = False) -> TestSet:
    """Giu test set co dinh giua cac lan chay; chi sinh lai khi chua co file hoac refresh=True."""
    path = Path(output_path)
    if path.exists() and not refresh:
        return TestSet(read_json(path))
    return TestSet(build_test_set(df, path))
