# Mathematical Optimization Papers RSS

An automatically updated RSS feed that aggregates the latest papers on **mathematical optimization** from [arXiv](https://arxiv.org/) and [Semantic Scholar](https://www.semanticscholar.org/). A GitHub Actions workflow fetches new papers every day and publishes the feed via GitHub Pages.

**Feed URL:** https://koki-kazaore.github.io/mathematical-optimization-papers-rss/feed.xml

## Features

- **Two sources** — pulls from arXiv (`math.OC`, `cs.MS`, `cs.LG`) and the Semantic Scholar bulk search API.
- **Topic filtering** — keeps papers matching optimization keywords (convex optimization, linear/integer/mixed-integer programming, stochastic, robust, combinatorial, semidefinite, and more). All `math.OC` papers pass through without keyword filtering.
- **Deduplication** — collapses the same paper appearing in multiple sources using a canonical ID (DOI → arXiv ID → normalized title/author/year fallback).
- **Stable "new" ordering** — persists a `first_seen_at` timestamp per paper in `data/state.json`, so the RSS `pubDate` reflects when a paper first entered the feed rather than its original publication date. Papers surface as new the day they are discovered.
- **Daily automation** — a scheduled GitHub Actions workflow regenerates the feed and commits any changes.

## How It Works

The pipeline runs end to end in [`main.py`](src/optimization_rss/main.py):

```
fetch (arXiv + Semantic Scholar)
  → deduplicate
  → keyword filter
  → assign first_seen_at (load/save state)
  → generate RSS feed
```

| Module | Responsibility |
| --- | --- |
| `config.py` | Central configuration: categories, keywords, queries, file paths, lookback window |
| `sources/arxiv.py` | Fetches and parses the arXiv Atom API (`math.OC` passthrough, others keyword-filtered) |
| `sources/semantic_scholar.py` | Fetches via the Semantic Scholar bulk search API with pagination |
| `dedupe.py` | Canonical IDs and cross-source deduplication |
| `filters.py` | Optimization keyword matching |
| `state.py` | Loads/saves `data/state.json` and assigns `first_seen_at` |
| `rss.py` | Builds the RSS 2.0 feed (newest first, capped at 500 items) |
| `main.py` | Orchestrates the full pipeline |

## Subscribing

### RSS reader

Add the feed URL to any RSS reader:

```
https://koki-kazaore.github.io/mathematical-optimization-papers-rss/feed.xml
```

### Slack

In any channel or DM, run:

```
/feed https://koki-kazaore.github.io/mathematical-optimization-papers-rss/feed.xml
```

New papers then arrive as Slack notifications when the feed updates. See the [landing page](https://koki-kazaore.github.io/mathematical-optimization-papers-rss/) for details.

## Local Development

Requires Python 3.11+.

```bash
# Install the package (exposes the `update-feed` console script)
pip install -e .

# Optional: a Semantic Scholar API key raises rate limits
cp .env.example .env   # then set SEMANTIC_SCHOLAR_API_KEY
export SEMANTIC_SCHOLAR_API_KEY=your_key_here

# Run the pipeline; writes docs/feed.xml and updates data/state.json
update-feed
```

The Semantic Scholar API key is optional — the run still works without it, just with lower rate limits. If the Semantic Scholar fetch fails, the pipeline logs the error and continues with arXiv results only.

## Configuration

Tunable parameters live in [`src/optimization_rss/config.py`](src/optimization_rss/config.py):

- `ARXIV_CATEGORIES` — arXiv categories to query.
- `OPTIMIZATION_KEYWORDS` — keywords used to filter non-`math.OC` and Semantic Scholar papers.
- `SEMANTIC_SCHOLAR_QUERIES` — search queries sent to Semantic Scholar.
- `LOOKBACK_DAYS` — how far back to consider papers (default: 7).
- `MAX_PAPERS_PER_SOURCE` — per-source fetch cap.

## Automation

[`.github/workflows/update-feed.yml`](.github/workflows/update-feed.yml) runs daily at 06:00 UTC (and on manual `workflow_dispatch`). It installs the package, runs `update-feed`, and commits `docs/feed.xml` and `data/state.json` if anything changed. The `SEMANTIC_SCHOLAR_API_KEY` is supplied via repository secrets.

## License

See [LICENSE](LICENSE).
