from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    title: str
    authors: list[str]
    abstract: str
    published_at: datetime
    first_seen_at: datetime
    doi: str | None
    arxiv_id: str | None
    paper_url: str
    pdf_url: str | None
    source: str
    source_ids: dict = field(default_factory=dict)
