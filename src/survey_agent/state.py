"""Shared state definition for the Paper Survey Agent graph."""

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
from operator import add
from pydantic import BaseModel, Field


class PaperMeta(BaseModel):
    """Metadata for a single paper."""
    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    url: Optional[str] = None
    citation_count: Optional[int] = None
    venue: Optional[str] = None
    importance_score: float = 0.0  # How strongly cited / emphasized in the source paper
    source: str = "extracted"  # extracted | backward | forward


class TermDefinition(BaseModel):
    """A term and its definitions / aliases."""
    canonical_term: str
    aliases: list[str] = Field(default_factory=list)
    definitions: list[str] = Field(default_factory=list)
    papers: list[str] = Field(default_factory=list)  # paper titles or ids


class SurveyMatrixRow(BaseModel):
    """One row in the survey matrix."""
    paper_title: str
    authors: str
    year: Optional[int] = None
    research_object: Optional[str] = None
    theory_framework: Optional[str] = None
    key_terms: list[str] = Field(default_factory=list)
    main_claim: Optional[str] = None
    methodology: Optional[str] = None
    limitations: Optional[str] = None


class ResearchGap(BaseModel):
    """Identified research gap or conflict."""
    description: str
    related_papers: list[str] = Field(default_factory=list)
    gap_type: str = "missing"  # missing | conflict | underexplored | methodological
    suggested_integration: Optional[str] = None


class SurveyState(TypedDict):
    """Main state passed through the LangGraph."""
    # Input
    pdf_path: str
    paper_title: Optional[str]
    paper_text: Optional[str]  # full extracted text or relevant sections

    # Parser Agent outputs
    related_work_text: Optional[str]
    references: list[PaperMeta]
    important_citations: list[PaperMeta]  # highly emphasized ones

    # Crawler Agent outputs
    backward_papers: list[PaperMeta]
    forward_papers: list[PaperMeta]
    all_papers: list[PaperMeta]  # merged unique papers

    # Ontology Agent outputs
    terms: list[TermDefinition]
    survey_matrix: list[SurveyMatrixRow]

    # Gap Agent outputs
    gaps: list[ResearchGap]
    synthesis: Optional[str]  # final narrative summary

    # Control / messages
    messages: Annotated[list[Any], add]
    errors: list[str]
    current_step: str
