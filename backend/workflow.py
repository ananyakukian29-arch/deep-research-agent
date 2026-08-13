from langgraph.graph import StateGraph, START, END
from backend.memory.state import AgentState
from backend.agents.orchestrator import orchestrator_node
from backend.agents.researcher import researcher_node
from backend.agents.synthesizer import synthesizer_node

# Bug 4 fix: maximum number of researcher iterations per graph run.
# researcher_node increments loop_count on every pass; route_research checks
# this value and hard-routes to synthesizer if the cap is reached, preventing
# infinite loops and runaway API costs.
MAX_LOOP_COUNT = 5

def topic_manager_node(state: AgentState) -> dict:
    """Picks the next topic from research_plan to process."""
    plan = list(state.get("research_plan", []))
    
    if plan:
        next_topic = plan.pop(0)
        return {
            "current_topic": next_topic,
            "research_plan": plan
        }
    else:
        return {
            "current_topic": "",
            "research_plan": []
        }

def route_research(state: AgentState) -> str:
    """Routes execution based on whether topics remain to be researched.

    Safety guard: if loop_count reaches MAX_LOOP_COUNT the router forces
    a transition to the synthesizer regardless of remaining topics, preventing
    an infinite loop from draining API quota.
    """
    loop_count = state.get("loop_count", 0)
    if loop_count >= MAX_LOOP_COUNT:
        # Hard exit — synthesize whatever has been collected so far.
        return "synthesizer"
    if state.get("current_topic"):
        return "researcher"
    return "synthesizer"

def build_graph():
    """Builds and compiles the multi-agent execution graph."""
    workflow = StateGraph(AgentState)

    # Define Nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("topic_manager", topic_manager_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define Edges
    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("orchestrator", "topic_manager")
    
    # Conditional routing: either process the topic or hand off to synthesis
    workflow.add_conditional_edges(
        "topic_manager",
        route_research,
        {
            "researcher": "researcher",
            "synthesizer": "synthesizer"
        }
    )
    
    # Loop back from researcher to topic_manager for the next sub-topic
    workflow.add_edge("researcher", "topic_manager")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()

# Instantiated graph object for import in UI
app_graph = build_graph()

if __name__ == "__main__":
    # Test execution via CLI
    initial_state = {
        "user_request": "Compare PyTorch vs TensorFlow in 2026 for production deployment.",
        "research_plan": [],
        "current_topic": "",
        "collected_research": [],
        "final_report": "",
        "loop_count": 0
    }
    
    print("Running research workflow...")
    result = app_graph.invoke(initial_state)
    print("\n=== FINAL REPORT ===\n")
    print(result.get("final_report", "No report generated."))