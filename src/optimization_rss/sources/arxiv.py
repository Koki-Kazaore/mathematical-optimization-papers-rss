import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser as dateutil_parser

from optimization_rss.config import ARXIV_CATEGORIES, LOOKBACK_DAYS, MAX_PAPERS_PER_SOURCE, OPTIMIZATION_KEYWORDS
from optimization_rss.models import Paper

ARXIV_API_URL = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _parse_entry(entry: ET.Element) -> Paper | None:
    title_el = entry.find("atom:title", NS)
    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

    abstract_el = entry.find("atom:summary", NS)
    abstract = abstract_el.text.strip().replace("\n", " ") if abstract_el is not None and abstract_el.text else ""

    authors = [
        name_el.text.strip()
        for author in entry.findall("atom:author", NS)
        if (name_el := author.find("atom:name", NS)) is not None and name_el.text
    ]

    published_el = entry.find("atom:published", NS)
    published_at = (
        dateutil_parser.parse(published_el.text)
        if published_el is not None and published_el.text
        else datetime.now(timezone.utc)
    )

    id_el = entry.find("atom:id", NS)
    arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""
    arxiv_id_raw = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else None
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id_raw) if arxiv_id_raw else None

    pdf_url = None
    doi = None
    for link in entry.findall("atom:link", NS):
        rel = link.get("rel", "")
        href = link.get("href", "")
        if link.get("type") == "application/pdf" or rel == "related":
            pdf_url = href
        doi_el = entry.find("arxiv:doi", NS)
        if doi_el is not None and doi_el.text:
            doi = doi_el.text.strip()

    paper_url = arxiv_url

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
        source="arxiv",
        source_ids={"arxiv": arxiv_id} if arxiv_id else {},
    )


def _matches_keywords(paper: Paper) -> bool:
    text = (paper.title + " " + paper.abstract).lower()
    return any(kw.lower() in text for kw in OPTIMIZATION_KEYWORDS)


def fetch_arxiv_papers() -> list[Paper]:
    papers: list[Paper] = []

    for i, category in enumerate(ARXIV_CATEGORIES):
        if i > 0:
            time.sleep(3)

        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": MAX_PAPERS_PER_SOURCE,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = requests.get(ARXIV_API_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[arxiv] Error fetching category {category}: {e}")
            continue

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            print(f"[arxiv] XML parse error for {category}: {e}")
            continue

        entries = root.findall("atom:entry", NS)
        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        fetched = 0
        for entry in entries:
            paper = _parse_entry(entry)
            if paper is None:
                continue

            if paper.published_at.tzinfo is None:
                paper.published_at = paper.published_at.replace(tzinfo=timezone.utc)
            if paper.published_at < cutoff:
                continue

            # math.OC: pass through all papers
            # cs.MS, cs.LG: filter by keywords
            if category == "math.OC" or _matches_keywords(paper):
                papers.append(paper)
                fetched += 1

        print(f"[arxiv] {category}: fetched {fetched} papers")

    return papers
