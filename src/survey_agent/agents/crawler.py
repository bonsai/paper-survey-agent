"""Crawler Agent: Backward / Forward citation collection via Semantic Scholar."""

from typing import Any
from survey_agent.state import SurveyState, PaperMeta
from survey_agent.tools.semantic_scholar import (
    search_paper,
    get_citations,
    get_references,
    dict_to_paper_meta,
)


def _find_best_match(title: str) -> dict | None:
    """Search Semantic Scholar and return the best matching paper dict."""
    results = search_paper(title, limit=3)
    if not results:
        return None
    # Simple heuristic: prefer exact-ish title match or highest citation count
    title_lower = title.lower().strip()
    for r in results:
        if (r.get("title") or "").lower().strip() == title_lower:
            return r
    return results[0]


def crawler_node(state: SurveyState) -> dict[str, Any]:
    """LangGraph node: enrich extracted papers and collect backward/forward citations."""
    references = state.get("references") or []
    important = state.get("important_citations") or []
    errors = list(state.get("errors") or [])
    messages = []

    # Prioritize important citations + high importance_score refs
    candidates = important + sorted(
        references, key=lambda p: p.importance_score, reverse=True
    )
    # Deduplicate by title
    seen_titles = set()
    unique_candidates: list[PaperMeta] = []
    for p in candidates:
        key = p.title.lower().strip()
        if key not in seen_titles and key:
            seen_titles.add(key)
            unique_candidates.append(p)

    backward: list[PaperMeta] = []
    forward: list[PaperMeta] = []
    enriched: list[PaperMeta] = []

    # Limit API calls for prototype (top 8 papers)
    for paper in unique_candidates[:8]:
        try:
            match = _find_best_match(paper.title)
            if not match or not match.get("paperId"):
                enriched.append(paper)
                continue

            meta = dict_to_paper_meta(match, source="semantic_scholar")
            meta.importance_score = paper.importance_score
            enriched.append(meta)

            paper_id = match["paperId"]

            # Backward: references of this paper
            refs = get_references(paper_id, limit=15)
            for r in refs:
                if r.get("title"):
                    backward.append(dict_to_paper_meta(r, source="backward"))

            # Forward: papers citing this one
            cites = get_citations(paper_id, limit=10)
            for c in cites:
                if c.get("title"):
                    forward.append(dict_to_paper_meta(c, source="forward"))

            messages.append(f"Crawled: {meta.title[:60]}...")

        except Exception as e:
            errors.append(f"Crawler error for '{paper.title[:40]}': {str(e)}")
            enriched.append(paper)

    # Merge all unique papers
    all_papers_map: dict[str, PaperMeta] = {}
    for p in enriched + backward + forward:
        key = p.title.lower().strip()
        if key and key not in all_papers_map:
            all_papers_map[key] = p
        elif key:
            # Keep the one with more metadata
            existing = all_papers_map[key]
            if (p.abstract and not existing.abstract) or (
                (p.citation_count or 0) > (existing.citation_count or 0)
            ):
                all_papers_map[key] = p

    all_papers = list(all_papers_map.values())

    return {
        "backward_papers": backward,
        "forward_papers": forward,
        "all_papers": all_papers,
        "references": enriched,  # update with richer metadata
        "current_step": "crawler_done",
        "messages": messages + [f"Crawler: total unique papers = {len(all_papers)}"],
        "errors": errors,
    }
