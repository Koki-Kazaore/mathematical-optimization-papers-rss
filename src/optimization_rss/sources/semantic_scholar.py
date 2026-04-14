from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser as dateutil_parser

from optimization_rss.config import (
    LOOKBACK_DAYS,
    MAX_PAPERS_PER_SOURCE,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_QUERIES,
)
from optimization_rss.models import Paper

BULK_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "title,url,abstract,authors,year,publicationDate,externalIds,openAccessPdf,publicationTypes"


def _build_headers() -> dict:
    headers = {"Accept": "application/json"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def _parse_paper(item: dict) -> Paper | None:
    title = item.get("title") or ""
    if not title:
        return None

    abstract = item.get("abstract") or ""
    authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]

    pub_date_str = item.get("publicationDate")
    if pub_date_str:
        try:
            published_at = dateutil_parser.parse(pub_date_str).replace(tzinfo=timezone.utc)
        except (ValueError, OverflowError):
            published_at = datetime.now(timezone.utc)
    elif item.get("year"):
        published_at = datetime(int(item["year"]), 1, 1, tzinfo=timezone.utc)
    else:
        published_at = datetime.now(timezone.utc)

    external_ids = item.get("externalIds") or {}
    doi = external_ids.get("DOI")
    arxiv_id = external_ids.get("ArXiv")

    paper_url = item.get("url") or ""
    if not paper_url and arxiv_id:
        paper_url = f"https://arxiv.org/abs/{arxiv_id}"

    open_access = item.get("openAccessPdf") or {}
    pdf_url = open_access.get("url")

    source_ids: dict = {}
    if doi:
        source_ids["doi"] = doi
    if arxiv_id:
        source_ids["arxiv"] = arxiv_id
    s2_id = item.get("paperId")
    if s2_id:
        source_ids["s2"] = s2_id

    return Paper(
        title=title,
        authors=authors,
        abstract=abstract,
        published_at=published_at,
        first_seen_at=datetime.now(timezone.utc),
        doi=doi,
        arxiv_id=arxiv_id,
        paper_url=paper_url,
        pdf_url=pdf_url,
        source="semantic_scholar",
        source_ids=source_ids,
    )


def fetch_semantic_scholar_papers() -> list[Paper]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    headers = _build_headers()
    papers: list[Paper] = []
    seen_ids: set[str] = set()

    for query in SEMANTIC_SCHOLAR_QUERIES:
        token = None
        query_count = 0

        while query_count < MAX_PAPERS_PER_SOURCE:
            params: dict = {
                "query": query,
                "fields": FIELDS,
                "limit": 100,
            }
            if token:
                params["token"] = token

            try:
                response = requests.get(BULK_SEARCH_URL, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                print(f"[semantic_scholar] Error fetching query '{query}': {e}")
                break
            except ValueError as e:
                print(f"[semantic_scholar] JSON parse error for query '{query}': {e}")
                break

            items = data.get("data", [])
            if not items:
                break

            stop_early = False
            for item in items:
                paper = _parse_paper(item)
                if paper is None:
                    continue

                # Stop paginating if paper is older than cutoff
                if paper.published_at < cutoff:
                    stop_early = True
                    continue

                # Deduplicate within this fetch using paper ID
                s2_id = item.get("paperId", "")
                if s2_id and s2_id in seen_ids:
                    continue
                if s2_id:
                    seen_ids.add(s2_id)

                papers.append(paper)
                query_count += 1

            token = data.get("token")
            if not token or stop_early:
                break

        print(f"[semantic_scholar] query='{query}': fetched {query_count} papers")

    return papers
