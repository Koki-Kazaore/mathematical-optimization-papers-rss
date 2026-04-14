import re
import unicodedata

from optimization_rss.models import Paper


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonical_id(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi}"
    if paper.arxiv_id:
        arxiv_id = re.sub(r"v\d+$", "", paper.arxiv_id)
        return f"arxiv:{arxiv_id}"

    first_author = _normalize(paper.authors[0]) if paper.authors else "unknown"
    title_norm = _normalize(paper.title)
    year = str(paper.published_at.year)
    return f"title:{title_norm[:80]}|{first_author[:40]}|{year}"


def deduplicate(papers: list[Paper]) -> list[Paper]:
    seen: dict[str, Paper] = {}
    for paper in papers:
        cid = canonical_id(paper)
        if cid not in seen:
            seen[cid] = paper
    return list(seen.values())
