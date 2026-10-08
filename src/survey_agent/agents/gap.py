"""Gap Discovery Agent: Identify research gaps and conflicts."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from survey_agent.state import SurveyState, ResearchGap


GAP_SYSTEM = """あなたは研究ギャップ発見の専門エージェントです。

与えられたサーベイマトリクスと用語情報を分析し、以下を抽出してください：

1. 先行研究で共通して見落とされている点（missing）
2. 議論が対立している部分（conflict）
3. まだ十分に探求されていない領域（underexplored）
4. 方法論的な限界が共通している点（methodological）

また、これらのギャップに対して「自分の研究をどうガッチャンコ（統合・応用）できるか」の候補も提案してください。

出力は必ず以下のJSON形式のみで返してください。

{
  "gaps": [
    {
      "description": "...",
      "related_papers": ["title1", "title2"],
      "gap_type": "missing|conflict|underexplored|methodological",
      "suggested_integration": "自分の研究をどう位置づけるかの提案"
    }
  ],
  "synthesis": "全体を通したサーベイの要約と、研究の立ち位置に関するナラティブ（日本語で）"
}
"""


def gap_node(state: SurveyState) -> dict[str, Any]:
    """LangGraph node: discover research gaps and produce synthesis."""
    matrix = state.get("survey_matrix") or []
    terms = state.get("terms") or []
    related_work = state.get("related_work_text") or ""
    errors = list(state.get("errors") or [])

    matrix_text = []
    for row in matrix:
        matrix_text.append(
            f"""■ {row.paper_title} ({row.authors}, {row.year or '?'})
  研究対象: {row.research_object or '-'}
  理論枠組み: {row.theory_framework or '-'}
  主要主張: {row.main_claim or '-'}
  手法: {row.methodology or '-'}
  限界: {row.limitations or '-'}
  キーワード: {', '.join(row.key_terms)}
"""
        )

    terms_text = []
    for t in terms:
        terms_text.append(
            f"- {t.canonical_term} (aliases: {', '.join(t.aliases)}) → {'; '.join(t.definitions[:2])}"
        )

    context = f"""【サーベイマトリクス】
{chr(10).join(matrix_text)}

【正規化用語】
{chr(10).join(terms_text)}

【元論文の関連研究テキスト（参考）】
{related_work[:4000]}
"""

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        response = llm.invoke(
            [
                SystemMessage(content=GAP_SYSTEM),
                HumanMessage(content=context),
            ]
        )

        content = response.content.strip()
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError("Failed to parse JSON from Gap LLM response")

        data = json.loads(json_match.group())

        gaps = [
            ResearchGap(
                description=g.get("description", ""),
                related_papers=g.get("related_papers") or [],
                gap_type=g.get("gap_type", "missing"),
                suggested_integration=g.get("suggested_integration"),
            )
            for g in data.get("gaps", [])
        ]

        return {
            "gaps": gaps,
            "synthesis": data.get("synthesis"),
            "current_step": "gap_done",
            "messages": [f"Gap Agent: found {len(gaps)} gaps"],
        }

    except Exception as e:
        errors.append(f"Gap error: {str(e)}")
        return {
            "errors": errors,
            "current_step": "gap_failed",
            "messages": [f"Gap failed: {str(e)}"],
        }
