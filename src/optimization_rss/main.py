from optimization_rss.config import ARXIV_CATEGORIES, FEED_FILE, STATE_FILE
from optimization_rss.dedupe import canonical_id, deduplicate
from optimization_rss.filters import matches_optimization_keywords
from optimization_rss.models import Paper
from optimization_rss.rss import generate_feed
from optimization_rss.sources.arxiv import fetch_arxiv_papers
from optimization_rss.sources.semantic_scholar import fetch_semantic_scholar_papers
from optimization_rss.state import assign_first_seen, load_state, save_state

# Categories where all papers pass through without keyword filtering
PASSTHROUGH_CATEGORIES = {"math.OC"}


def _is_passthrough(paper: Paper) -> bool:
    # arXiv papers from passthrough categories skip keyword filtering
    if paper.source == "arxiv" and paper.arxiv_id:
        # source_ids may contain category hint; we rely on the fetch logic
        # math.OC papers are already filtered at fetch time in arxiv.py
        return True
    return False


def main() -> None:
    # 1. Load state
    state = load_state(STATE_FILE)
    print(f"[main] Loaded state with {len(state)} known papers")

    # 2. Fetch from arXiv
    print("[main] Fetching from arXiv...")
    arxiv_papers = fetch_arxiv_papers()
    print(f"[main] arXiv: {len(arxiv_papers)} papers fetched")

    # 3. Fetch from Semantic Scholar (catch errors gracefully)
    print("[main] Fetching from Semantic Scholar...")
    try:
        ss_papers = fetch_semantic_scholar_papers()
        print(f"[main] Semantic Scholar: {len(ss_papers)} papers fetched")
    except Exception as e:
        print(f"[main] Semantic Scholar fetch failed: {e}")
        ss_papers = []

    # 4. Combine all papers
    all_papers = arxiv_papers + ss_papers

    # 5. Deduplicate
    all_papers = deduplicate(all_papers)
    print(f"[main] After deduplication: {len(all_papers)} papers")

    # 6. Filter Semantic Scholar papers by keywords
    #    (arXiv papers are already filtered at fetch time:
    #     math.OC passes all, cs.MS/cs.LG filtered by keywords)
    filtered: list[Paper] = []
    for paper in all_papers:
        if paper.source == "arxiv":
            filtered.append(paper)
        elif matches_optimization_keywords(paper):
            filtered.append(paper)
    print(f"[main] After keyword filtering: {len(filtered)} papers")

    # 7. assign_first_seen
    new_count_before = sum(1 for p in filtered if canonical_id(p) not in state)
    papers_with_seen, updated_state = assign_first_seen(filtered, state)
    new_count = len(updated_state) - len(state)

    # 8. Save updated state
    save_state(STATE_FILE, updated_state)
    print(f"[main] State saved ({len(updated_state)} total known papers)")

    # 9. Generate feed from current batch (up to 500 newest)
    generate_feed(papers_with_seen, FEED_FILE)

    # 10. Print summary
    print(f"\n[main] Summary: {new_count} new papers found (total in feed: {len(papers_with_seen)})")


if __name__ == "__main__":
    main()
