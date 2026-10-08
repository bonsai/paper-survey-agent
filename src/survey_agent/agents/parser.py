"""Parser Agent: Extract Related Work and References from PDF."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from survey_agent.state import SurveyState, PaperMeta
from survey_agent.tools.pdf_tools import extract_text_from_pdf, extract_sections


PARSER_SYSTEM = """あなたは学術論文の解析専門エージェントです。
与えられた論文テキストから以下を抽出してください：

1. Related Work / 従来技術 / 関連研究 セクションの全文
2. 参考文献リスト（可能な限りタイトル・著者・年を構造化）
3. 本文中で特に重要視されている（詳しく議論されている、複数回言及されている、肯定的に評価されている）先行研究

出力は必ず以下のJSON形式のみで返してください。余計な文章は不要です。

{
  "related_work": "...",
  "references": [
    {"title": "...", "authors": ["..."], "year": 2020, "importance_score": 0.8}
  ],
  "important_citations": [
    {"title": "...", "authors": ["..."], "year": 2020, "importance_score": 0.9, "reason": "..."}
  ]
}

importance_score は 0.0〜1.0 で、本文での扱いの重みを示してください。
"""


def parser_node(state: SurveyState) -> dict[str, Any]:
    """LangGraph node: parse PDF and extract references / related work."""
    pdf_path = state["pdf_path"]
    errors = list(state.get("errors") or [])

    try:
        full_text = extract_text_from_pdf(pdf_path)
        sections = extract_sections(full_text)

        related_work = sections.get("related_work") or sections.get("introduction") or ""
        references_text = sections.get("references") or ""

        # Prefer focused context for the LLM
        context = f"""【Related Work / 関連研究セクション】
{related_work[:12000]}

【References / 参考文献セクション】
{references_text[:8000]}
"""

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        response = llm.invoke(
            [
                SystemMessage(content=PARSER_SYSTEM),
                HumanMessage(content=context),
            ]
        )

        content = response.content.strip()
        # Extract JSON even if wrapped in markdown
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError("Failed to parse JSON from LLM response")

        data = json.loads(json_match.group())

        references = [
            PaperMeta(
                title=r.get("title", "Unknown"),
                authors=r.get("authors") or [],
                year=r.get("year"),
                importance_score=float(r.get("importance_score", 0.5)),
                source="extracted",
            )
            for r in data.get("references", [])
        ]

        important = [
            PaperMeta(
                title=r.get("title", "Unknown"),
                authors=r.get("authors") or [],
                year=r.get("year"),
                importance_score=float(r.get("importance_score", 0.8)),
                source="extracted",
            )
            for r in data.get("important_citations", [])
        ]

        return {
            "paper_text": full_text[:50000],  # keep a truncated version
            "related_work_text": data.get("related_work") or related_work,
            "references": references,
            "important_citations": important,
            "current_step": "parser_done",
            "messages": [f"Parser: extracted {len(references)} references, {len(important)} important citations"],
        }

    except Exception as e:
        errors.append(f"Parser error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "parser_failed",
            "messages": [f"Parser failed: {str(e)}"],
        }
