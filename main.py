#!/usr/bin/env python3
"""CLI entrypoint for Paper Survey Agent."""

import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

load_dotenv()

from survey_agent.graph import survey_graph
from survey_agent.state import SurveyState

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Paper Survey Agent - Automated literature survey with LangGraph"
    )
    parser.add_argument("pdf", type=str, help="Path to the target PDF paper")
    parser.add_argument(
        "--output", "-o", type=str, default="./outputs", help="Output directory"
    )
    parser.add_argument(
        "--title", type=str, default=None, help="Optional paper title override"
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        console.print(f"[red]PDF not found: {pdf_path}[/red]")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel.fit(
        "[bold blue]Paper Survey Agent[/bold blue]\n"
        "Parser → Crawler → Ontology → Gap Discovery",
        title="Starting",
    ))

    initial_state: SurveyState = {
        "pdf_path": str(pdf_path.resolve()),
        "paper_title": args.title,
        "paper_text": None,
        "related_work_text": None,
        "references": [],
        "important_citations": [],
        "backward_papers": [],
        "forward_papers": [],
        "all_papers": [],
        "terms": [],
        "survey_matrix": [],
        "gaps": [],
        "synthesis": None,
        "messages": [],
        "errors": [],
        "current_step": "start",
    }

    # Run the graph
    console.print("[cyan]Running multi-agent pipeline...[/cyan]")
    final_state = survey_graph.invoke(initial_state)

    # Pretty print results
    for msg in final_state.get("messages", []):
        console.print(f"  • {msg}")

    if final_state.get("errors"):
        console.print("[yellow]Warnings / Errors:[/yellow]")
        for e in final_state["errors"]:
            console.print(f"  [red]• {e}[/red]")

    # Survey Matrix table
    matrix = final_state.get("survey_matrix") or []
    if matrix:
        table = Table(title="Survey Matrix", show_lines=True)
        table.add_column("Paper", style="cyan", max_width=40)
        table.add_column("Year", justify="center")
        table.add_column("Object", max_width=25)
        table.add_column("Claim", max_width=40)
        for row in matrix:
            table.add_row(
                row.paper_title[:40],
                str(row.year or "?"),
                (row.research_object or "-")[:25],
                (row.main_claim or "-")[:40],
            )
        console.print(table)

    # Gaps
    gaps = final_state.get("gaps") or []
    if gaps:
        console.print("\n[bold magenta]Identified Research Gaps[/bold magenta]")
        for i, g in enumerate(gaps, 1):
            console.print(f"\n[bold]{i}. [{g.gap_type}][/bold] {g.description}")
            if g.suggested_integration:
                console.print(f"   → Integration idea: {g.suggested_integration}")

    # Synthesis
    if final_state.get("synthesis"):
        console.print(Panel(Markdown(final_state["synthesis"]), title="Synthesis"))

    # Save full JSON output
    def serialize(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return obj

    output_data = {
        "pdf": str(pdf_path),
        "current_step": final_state.get("current_step"),
        "references": [serialize(p) for p in final_state.get("references") or []],
        "all_papers_count": len(final_state.get("all_papers") or []),
        "terms": [serialize(t) for t in final_state.get("terms") or []],
        "survey_matrix": [serialize(r) for r in matrix],
        "gaps": [serialize(g) for g in gaps],
        "synthesis": final_state.get("synthesis"),
        "messages": final_state.get("messages"),
        "errors": final_state.get("errors"),
    }

    out_file = output_dir / f"survey_{pdf_path.stem}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[green]Full results saved to:[/green] {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
