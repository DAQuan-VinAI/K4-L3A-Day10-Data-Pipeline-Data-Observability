from __future__ import annotations

import random
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import build_text_for_embedding

SEED = 42
DROP_LATEST_RATIO = 0.2
BLANK_SUMMARY_ROWS = 3
NOISE_ROWS = 3
TRUNCATE_TITLE_ROWS = 3
TRUNCATED_TITLE_CHARS = 7
STALE_DATE_ROWS = 6  # Du de day stale ratio vuot nguong 25% cua freshness SLA.
STALE_SHIFT_DAYS = 5 * 365
DUPLICATE_ROWS = 5  # Bu lai so dong da drop -> tong so dong khong doi (silent failure).
NOISE_TOKENS = ["@@##", "lorem", "ipsum", "%%%", "0xDEADBEEF", "¿¿", "zzkq", "<null>", "~~~"]


def _scenario(name: str, description: str, df: pd.DataFrame, **details: Any) -> dict[str, Any]:
    return {
        "scenario": name,
        "description": description,
        "affected_rows": int(len(df)),
        "paper_ids": df["paper_id"].tolist(),
        **details,
    }


def _noise(rng: random.Random) -> str:
    return " ".join(rng.choice(NOISE_TOKENS) for _ in range(6))


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Tiem 6 kich ban loi du lieu co kiem soat (deterministic theo SEED) va ghi log chi tiet."""
    rng = random.Random(SEED)
    corrupted = df.copy().reset_index(drop=True)
    log: list[dict[str, Any]] = []

    # 1. Drop latest records: mat du lieu tuoi nhat.
    drop_count = max(1, round(len(corrupted) * DROP_LATEST_RATIO))
    latest = corrupted.sort_values(["published", "paper_id"], ascending=[False, True]).head(drop_count)
    log.append(_scenario("drop_latest_records", f"Bo {drop_count} bai bao moi nhat ({DROP_LATEST_RATIO:.0%})", latest))
    corrupted = corrupted.drop(index=latest.index).reset_index(drop=True)

    # Cac kich ban 2-5 tac dong len cac dong khac nhau de log ro rang, khong chong cheo.
    targets = rng.sample(
        list(corrupted.index),
        BLANK_SUMMARY_ROWS + NOISE_ROWS + TRUNCATE_TITLE_ROWS + STALE_DATE_ROWS,
    )
    cursor = 0

    def take(count: int) -> list[int]:
        nonlocal cursor
        picked = targets[cursor : cursor + count]
        cursor += count
        return picked

    # 2. Blank summary: scraper tra ve abstract rong.
    rows = take(BLANK_SUMMARY_ROWS)
    log.append(_scenario("blank_summary", "Xoa trang summary", corrupted.loc[rows]))
    corrupted.loc[rows, "summary"] = ""

    # 3. Inject text noise: chen chuoi rac vao summary (lan sang text_for_embedding khi rebuild).
    rows = take(NOISE_ROWS)
    noises = {row: _noise(rng) for row in rows}
    log.append(_scenario("inject_text_noise", "Chen ky tu rac vao summary/text_for_embedding", corrupted.loc[rows], noise=list(noises.values())))
    for row, noise in noises.items():
        words = corrupted.at[row, "summary"].split()
        position = rng.randint(0, len(words))
        corrupted.at[row, "summary"] = " ".join(words[:position] + [noise] + words[position:])

    # 4. Truncate title: tieu de bi cat cut con < 8 ky tu.
    rows = take(TRUNCATE_TITLE_ROWS)
    log.append(
        _scenario(
            "truncate_title",
            f"Cat title con {TRUNCATED_TITLE_CHARS} ky tu",
            corrupted.loc[rows],
            original_titles=corrupted.loc[rows, "title"].tolist(),
        )
    )
    corrupted.loc[rows, "title"] = corrupted.loc[rows, "title"].str[:TRUNCATED_TITLE_CHARS].str.strip()

    # 5. Stale date: lui ngay xuat ban ve 5 nam truoc.
    rows = take(STALE_DATE_ROWS)
    original_dates = corrupted.loc[rows, "published"].astype(str).tolist()
    shifted = pd.to_datetime(corrupted.loc[rows, "published"]) - pd.Timedelta(days=STALE_SHIFT_DAYS)
    corrupted.loc[rows, "published"] = shifted.dt.strftime("%Y-%m-%d")
    corrupted.loc[rows, "age_days"] = corrupted.loc[rows, "age_days"].astype(int) + STALE_SHIFT_DAYS
    log.append(
        _scenario(
            "stale_date",
            f"Lui published {STALE_SHIFT_DAYS} ngay (~5 nam)",
            corrupted.loc[rows],
            original_published=original_dates,
            corrupted_published=corrupted.loc[rows, "published"].tolist(),
        )
    )

    # 6. Duplicate rows: nap trung ban ghi, bu dung so dong da drop.
    duplicate_rows = rng.sample(list(corrupted.index), min(DUPLICATE_ROWS, len(corrupted)))
    duplicates = corrupted.loc[duplicate_rows]
    log.append(_scenario("duplicate_rows", "Nhan doi ban ghi (trung paper_id)", duplicates))
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    # 7. Rebuild cac cot dan xuat de loi lan vao du lieu embedding.
    corrupted["summary_chars"] = corrupted["summary"].str.len().astype(int)
    corrupted["text_for_embedding"] = corrupted.apply(build_text_for_embedding, axis=1)

    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "seed": SEED,
            "input_rows": int(len(df)),
            "output_rows": int(len(corrupted)),
            "scenario_count": len(log),
            "scenarios": log,
        },
    )
    return corrupted
