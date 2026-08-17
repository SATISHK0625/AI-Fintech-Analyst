from langgraph.graph import StateGraph, END
from app.agents.state import FinancialState
from app.agents.planner import planner_node
from app.agents.retrieval import retrieval_node
from app.agents.analysis import analysis_node
from app.agents.audit import audit_node
from app.agents.recommendation import recommendation_node
from app.agents.report import report_node

def build_financial_multi_agent_graph():
    """Builds and compiles the LangGraph Multi-Agent Financial Workflow."""
    workflow = StateGraph(FinancialState)

    # 1. Add Agent Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("audit", audit_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("report", report_node)

    # 2. Set Entry Point
    workflow.set_entry_point("planner")

    # 3. Define Graph Edges (Sequential Multi-Agent Pipeline)
    workflow.add_edge("planner", "retrieval")
    workflow.add_edge("retrieval", "analysis")
    workflow.add_edge("analysis", "audit")
    workflow.add_edge("audit", "recommendation")
    workflow.add_edge("recommendation", "report")
    workflow.add_edge("report", END)

    # 4. Compile Graph
    return workflow.compile()

# Instantiated Multi-Agent Engine Graph
financial_graph = build_financial_multi_agent_graph()

def run_financial_agent_workflow(user_query: str, company_id: int = 1) -> FinancialState:
    """Executes the compiled multi-agent state graph."""
    initial_state: FinancialState = {
        "user_query": user_query,
        "company_id": company_id,
        "plan": None,
        "retrieved_data": None,
        "analysis_results": None,
        "audit_results": None,
        "recommendation_results": None,
        "report_results": None,
        "agent_logs": [],
        "error": None
    }
    
    final_state = financial_graph.invoke(initial_state)
    return final_state
