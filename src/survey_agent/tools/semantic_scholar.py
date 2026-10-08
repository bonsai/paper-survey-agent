"""Semantic Scholar API client for paper metadata and citation graph."""

import os
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from survey_agent.state import PaperMeta

BASE_URL = "https://api.semanticscholar.org/graph/v1"


def _headers() -> dict:
    headers = {"User-Agent": "paper-survey-agent/0.1"}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def search_paper(title: str, limit: int = 5) -> list[dict]:
    """Search papers by title."""
    params = {
        "query": title,
        "limit": limit,
        "fields": "title,authors,year,abstract,externalIds,citationCount,venue,url",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{BASE_URL}/paper/search", params=params, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_paper(paper_id: str) -> Optional[dict]:
    """Get paper details by Semantic Scholar ID, DOI, or ArXiv ID."""
    fields = "title,authors,year,abstract,externalIds,citationCount,venue,url,references,citations"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{BASE_URL}/paper/{paper_id}",
            params={"fields": fields},
            headers=_headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_citations(paper_id: str, limit: int = 20) -> list[dict]:
    """Get papers that cite this paper (forward citations)."""
    params = {
        "fields": "title,authors,year,abstract,externalIds,citationCount,venue,url",
        "limit": limit,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{BASE_URL}/paper/{paper_id}/citations",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return [item.get("citingPaper", {}) for item in data.get("data", [])]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_references(paper_id: str, limit: int = 50) -> list[dict]:
    """Get papers referenced by this paper (backward)."""
    params = {
        "fields": "title,authors,year,abstract,externalIds,citationCount,venue,url",
        "limit": limit,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{BASE_URL}/paper/{paper_id}/references",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return [item.get("citedPaper", {}) for item in data.get("data", [])]


def dict_to_paper_meta(data: dict, source: str = "semantic_scholar") -> PaperMeta:
    """Convert Semantic Scholar response to PaperMeta."""
    authors = [a.get("name", "") for a in data.get("authors", []) if a.get("name")]
    external = data.get("externalIds") or {}
    return PaperMeta(
        title=data.get("title") or "Unknown",
        authors=authors,
        year=data.get("year"),
        abstract=data.get("abstract"),
        doi=external.get("DOI"),
        arxiv_id=external.get("ArXiv"),
        semantic_scholar_id=data.get("paperId"),
        url=data.get("url"),
        citation_count=data.get("citationCount"),
        venue=data.get("venue"),
        source=source,
    )
