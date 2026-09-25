from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import html
import logging
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 20

_TAG_PATTERN = re.compile(r"<[^>]+>")
_DOI_PREFIX_PATTERN = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def normalize_doi(value: str | None) -> str:
    doi = normalize_whitespace(value or "")
    return _DOI_PREFIX_PATTERN.sub("", doi).strip().lower()


def strip_markup(value: str | None) -> str:
    """Bo the HTML/JATS XML (vd `<jats:p>`) va unescape entity, roi chuan hoa khoang trang."""
    without_tags = _TAG_PATTERN.sub(" ", value or "")
    return normalize_whitespace(html.unescape(without_tags))


def _date_from_parts(field: dict | None) -> str | None:
    parts = ((field or {}).get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return None
    year, month, day = (list(parts) + [1, 1])[:3]
    try:
        return datetime(int(year), int(month or 1), int(day or 1)).date().isoformat()
    except (TypeError, ValueError):
        return None


def _date_from_datetime(field: dict | None) -> str | None:
    value = (field or {}).get("date-time")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _parse_published(item: dict) -> str | None:
    for key in ("published", "published-print", "published-online", "issued"):
        parsed = _date_from_parts(item.get(key))
        if parsed:
            return parsed
    return _date_from_datetime(item.get("created"))


def _parse_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        name = normalize_whitespace(f"{author.get('given', '')} {author.get('family', '')}")
        name = name or normalize_whitespace(author.get("name", ""))
        if name:
            authors.append(name)
    return authors


def _parse_pdf_url(item: dict, fallback: str) -> str:
    for link in item.get("link") or []:
        if link.get("content-type") == "application/pdf" and link.get("URL"):
            return link["URL"]
    return fallback


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    for item in (payload.get("message") or {}).get("items") or []:
        paper_id = normalize_doi(item.get("DOI"))
        title = normalize_whitespace(" ".join(item.get("title") or []))
        summary = strip_markup(item.get("abstract"))
        published = _parse_published(item)
        if not (paper_id and title and summary and published):
            logger.warning("Bo qua record Crossref khong hop le: DOI=%r", item.get("DOI"))
            continue

        categories = [normalize_whitespace(subject) for subject in item.get("subject") or []]
        categories = [category for category in categories if category]
        updated = (
            _date_from_datetime(item.get("updated"))
            or _date_from_datetime(item.get("indexed"))
            or published
        )
        abs_url = item.get("URL") or f"https://doi.org/{paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_parse_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=_parse_pdf_url(item, abs_url),
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def _request_crossref(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            last_error = RuntimeError(f"Crossref tra ve HTTP {response.status_code}")
            if response.status_code not in RETRYABLE_STATUS_CODES:
                break
        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Khong goi duoc Crossref sau {MAX_ATTEMPTS} lan thu: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Dual-mode ingestion: live API khi REFRESH_SOURCE=1, fallback ve snapshot khi 429/mat mang."""
    snapshot_path = settings.paths.raw_api_response
    payload: dict | None = None

    if settings.refresh_source or not snapshot_path.exists():
        try:
            payload = _request_crossref(settings)
            records = parse_crossref_payload(payload)
            if not records:
                raise RuntimeError("Crossref tra ve 0 record hop le")
            write_json(snapshot_path, payload)
        except (RuntimeError, ValueError) as exc:
            if not snapshot_path.exists():
                raise
            logger.warning("Live API loi (%s) -> chuyen sang snapshot offline %s", exc, snapshot_path)
            payload = None

    if payload is None:
        payload = read_json(snapshot_path)
        records = parse_crossref_payload(payload)

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    return [PaperRecord(**row) for row in read_json(path)]
