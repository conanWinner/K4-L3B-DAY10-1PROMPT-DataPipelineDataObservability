from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


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


def _strip_markup(value: str) -> str:
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", value or ""))


def _first_text(value) -> str:
    if isinstance(value, list):
        return _strip_markup(value[0]) if value else ""
    return _strip_markup(value or "")


def _date_from_parts(field: dict | None) -> str:
    parts = ((field or {}).get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return ""
    year, month, day = (list(parts) + [1, 1])[:3]
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _author_names(authors: list[dict] | None) -> list[str]:
    names = []
    for author in authors or []:
        name = normalize_whitespace(f"{author.get('given', '')} {author.get('family', '')}")
        name = name or normalize_whitespace(author.get("name", ""))
        if name:
            names.append(name)
    return names


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    seen: set[str] = set()
    for item in payload.get("message", {}).get("items", []):
        paper_id = normalize_whitespace(item.get("DOI", "")).lower()
        title = _first_text(item.get("title"))
        summary = _strip_markup(item.get("abstract", ""))
        if not paper_id or not title or not summary or paper_id in seen:
            continue

        published = (
            _date_from_parts(item.get("published"))
            or _date_from_parts(item.get("published-print"))
            or _date_from_parts(item.get("published-online"))
            or _date_from_parts(item.get("issued"))
        )
        if not published:
            continue
        updated = (item.get("created", {}).get("date-time") or published)[:10]

        categories = [normalize_whitespace(subject) for subject in item.get("subject", []) if subject]
        abs_url = item.get("URL") or f"https://doi.org/{paper_id}"
        pdf_url = next(
            (link.get("URL") for link in item.get("link", []) if "pdf" in link.get("content-type", "")),
            abs_url,
        )

        seen.add(paper_id)
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_author_names(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def _request_crossref(settings: Settings, retries: int = 3) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,published-print,published-online,issued,created,URL,link",
    }
    for attempt in range(retries):
        response = requests.get(CROSSREF_WORKS_URL, params=params, timeout=30)
        if response.status_code in RETRY_STATUS_CODES and attempt < retries - 1:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Crossref API retries exhausted.")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    snapshot_path = settings.paths.raw_api_response
    payload = None
    if settings.refresh_source or not snapshot_path.exists():
        try:
            payload = _request_crossref(settings)
            if not parse_crossref_payload(payload):
                raise ValueError("Crossref API returned no usable records.")
            write_json(snapshot_path, payload)
        except Exception as exc:
            if not snapshot_path.exists():
                raise
            print(f"[crossref] API unavailable ({exc}); falling back to local snapshot {snapshot_path.name}.")
            payload = None
    if payload is None:
        payload = read_json(snapshot_path)

    records = parse_crossref_payload(payload)[: settings.max_results]
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    return [PaperRecord(**row) for row in read_json(path)]
