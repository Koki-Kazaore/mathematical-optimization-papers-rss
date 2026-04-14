from optimization_rss.config import OPTIMIZATION_KEYWORDS
from optimization_rss.models import Paper


def matches_optimization_keywords(paper: Paper) -> bool:
    text = (paper.title + " " + paper.abstract).lower()
    return any(kw.lower() in text for kw in OPTIMIZATION_KEYWORDS)
