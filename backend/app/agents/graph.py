from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents.agents import (
    detection_agent,
    geomorphology_agent,
    interpretation_agent,
    intrusion_agent
)

def build_dro_mind_graph():
    """
    Builds the LangGraph state machine orchestrating the DroMIND agents.
    Flow:
      START -> Detection Agent -> Geomorphology Agent -> Operational Agent -> Intrusion Agent -> END
    Each agent updates a portion of the shared AgentState.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes to graph
    workflow.add_node("detection_agent", detection_agent)
    workflow.add_node("geomorphology_agent", geomorphology_agent)
    workflow.add_node("interpretation_agent", interpretation_agent)
    workflow.add_node("intrusion_agent", intrusion_agent)
    
    # Add sequential workflow transitions (propagates state through updates)
    workflow.add_edge(START, "detection_agent")
    workflow.add_edge("detection_agent", "geomorphology_agent")
    workflow.add_edge("geomorphology_agent", "interpretation_agent")
    workflow.add_edge("interpretation_agent", "intrusion_agent")
    workflow.add_edge("intrusion_agent", END)
    
    # Compile
    app = workflow.compile()
    return app

# Singleton compiled graph instance
dro_mind_graph = build_dro_mind_graph()
