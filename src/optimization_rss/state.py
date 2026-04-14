import json
from datetime import datetime, timezone
from pathlib import Path

from optimization_rss.dedupe import canonical_id
from optimization_rss.models import Paper


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def assign_first_seen(
    papers: list[Paper], state: dict
) -> tuple[list[Paper], dict]:
    now = datetime.now(timezone.utc)
    updated_state = dict(state)
    result: list[Paper] = []

    for paper in papers:
        cid = canonical_id(paper)
        if cid in updated_state:
            paper.first_seen_at = datetime.fromisoformat(updated_state[cid])
        else:
            paper.first_seen_at = now
            updated_state[cid] = now.isoformat()
        result.append(paper)

    return result, updated_state
