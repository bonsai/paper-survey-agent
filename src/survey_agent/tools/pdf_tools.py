"""PDF extraction utilities."""

from pathlib import Path
from typing import Optional
import pdfplumber
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract full text from a PDF using pdfplumber (better layout awareness)."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n\n".join(texts)


def extract_text_pypdf(pdf_path: str | Path) -> str:
    """Fallback extraction with pypdf."""
    reader = PdfReader(str(pdf_path))
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text)
    return "\n\n".join(texts)


def extract_sections(text: str) -> dict[str, str]:
    """
    Heuristic section extraction for academic papers.
    Looks for common headings: Abstract, Introduction, Related Work, References, etc.
    """
    import re

    section_patterns = [
        ("abstract", r"(?i)^\s*(abstract|要旨)\s*$"),
        ("introduction", r"(?i)^\s*(1\.?\s*)?(introduction|はじめに|序論)\s*$"),
        ("related_work", r"(?i)^\s*(\d\.?\s*)?(related\s+work|background|previous\s+work|従来技術|関連研究|先行研究)\s*$"),
        ("method", r"(?i)^\s*(\d\.?\s*)?(method|methodology|approach|提案手法)\s*$"),
        ("results", r"(?i)^\s*(\d\.?\s*)?(results?|experiments?|evaluation|実験|結果)\s*$"),
        ("discussion", r"(?i)^\s*(\d\.?\s*)?(discussion|考察)\s*$"),
        ("conclusion", r"(?i)^\s*(\d\.?\s*)?(conclusion|まとめ|結論)\s*$"),
        ("references", r"(?i)^\s*(references|bibliography|参考文献)\s*$"),
    ]

    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current = "preamble"
    sections[current] = []

    for line in lines:
        matched = False
        for name, pattern in section_patterns:
            if re.match(pattern, line.strip()):
                current = name
                sections.setdefault(current, [])
                matched = True
                break
        if not matched:
            sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}
