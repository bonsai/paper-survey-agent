"""LangGraph definition for the Paper Survey Agent pipeline."""

from langgraph.graph import StateGraph, END

from survey_agent.state import SurveyState
from survey_agent.agents.parser import parser_node
from survey_agent.agents.crawler import crawler_node
from survey_agent.agents.ontology import ontology_node
from survey_agent.agents.gap import gap_node


def build_survey_graph():
    """Build and compile the 4-agent survey graph."""
    graph = StateGraph(SurveyState)

    # Nodes
    graph.add_node("parser", parser_node)
    graph.add_node("crawler", crawler_node)
    graph.add_node("ontology", ontology_node)
    graph.add_node("gap", gap_node)

    # Linear flow for the prototype
    graph.set_entry_point("parser")
    graph.add_edge("parser", "crawler")
    graph.add_edge("crawler", "ontology")
    graph.add_edge("ontology", "gap")
    graph.add_edge("gap", END)

    return graph.compile()


# Convenience compiled instance
survey_graph = build_survey_graph()
