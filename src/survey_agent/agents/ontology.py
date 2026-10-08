"""Ontology Agent: Normalize terms and build survey matrix."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from survey_agent.state import SurveyState, TermDefinition, SurveyMatrixRow


ONTOLOGY_SYSTEM = """あなたは学術用語の正規化とサーベイマトリクス作成の専門エージェントです。

与えられた論文群のタイトル・アブストラクト・関連研究テキストを分析し、以下を行ってください：

1. 用語の揺れを吸収した「正規化用語リスト」を作成
   - 同じ現象・概念を指す異なる表記をグループ化
   - 各グループに canonical_term（標準名）と aliases を付ける

2. サーベイマトリクス（対比表）を作成
   - 各論文について：研究対象、用いた理論・枠組み、主要主張、手法、限界を整理

出力は必ず以下のJSON形式のみで返してください。

{
  "terms": [
    {
      "canonical_term": "...",
      "aliases": ["...", "..."],
      "definitions": ["..."],
      "papers": ["paper title 1", "paper title 2"]
    }
  ],
  "survey_matrix": [
    {
      "paper_title": "...",
      "authors": "Author1, Author2",
      "year": 2020,
      "research_object": "...",
      "theory_framework": "...",
      "key_terms": ["term1", "term2"],
      "main_claim": "...",
      "methodology": "...",
      "limitations": "..."
    }
  ]
}
"""


def ontology_node(state: SurveyState) -> dict[str, Any]:
    """LangGraph node: build term dictionary and survey matrix."""
    all_papers = state.get("all_papers") or []
    related_work = state.get("related_work_text") or ""
    errors = list(state.get("errors") or [])

    # Prepare compact context (limit size)
    paper_summaries = []
    for p in all_papers[:25]:  # cap for token limits
        authors = ", ".join(p.authors[:3])
        abstract = (p.abstract or "")[:400]
        paper_summaries.append(
            f"- {p.title} ({authors}, {p.year or '?'})\n  Abstract: {abstract}"
        )

    context = f"""【関連研究テキスト（抜粋）】
{related_work[:6000]}

【収集した論文一覧】
{chr(10).join(paper_summaries)}
"""

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        response = llm.invoke(
            [
                SystemMessage(content=ONTOLOGY_SYSTEM),
                HumanMessage(content=context),
            ]
        )

        content = response.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError("Failed to parse JSON from Ontology LLM response")

        data = json.loads(json_match.group())

        terms = [
            TermDefinition(
                canonical_term=t.get("canonical_term", ""),
                aliases=t.get("aliases") or [],
                definitions=t.get("definitions") or [],
                papers=t.get("papers") or [],
            )
            for t in data.get("terms", [])
        ]

        matrix = [
            SurveyMatrixRow(
                paper_title=r.get("paper_title", ""),
                authors=r.get("authors", ""),
                year=r.get("year"),
                research_object=r.get("research_object"),
                theory_framework=r.get("theory_framework"),
                key_terms=r.get("key_terms") or [],
                main_claim=r.get("main_claim"),
                methodology=r.get("methodology"),
                limitations=r.get("limitations"),
            )
            for r in data.get("survey_matrix", [])
        ]

        return {
            "terms": terms,
            "survey_matrix": matrix,
            "current_step": "ontology_done",
            "messages": [
                f"Ontology: {len(terms)} term groups, {len(matrix)} matrix rows"
            ],
        }

    except Exception as e:
        errors.append(f"Ontology error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "ontology_failed",
            "messages": [f"Ontology failed: {str(e)}"],
        }
