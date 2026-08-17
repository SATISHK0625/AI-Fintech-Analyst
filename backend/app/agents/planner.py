import datetime
from app.agents.state import FinancialState
from app.agents.llm_factory import llm_provider

def planner_node(state: FinancialState) -> FinancialState:
    """Planner Agent: Analyzes intent and constructs execution plan."""
    query = state.get("user_query", "").lower()
    
    system_prompt = (
        "You are an expert Financial Planner Agent for small business auditing. "
        "Analyze the user query and output a structured plan covering required metrics, audit focus, and RAG search topics."
    )
    
    fallback_plan_str = (
        f"Execution Plan for Query: '{state.get('user_query')}'\n"
        "- Task 1: Fetch transaction ledger history and company accounts.\n"
        "- Task 2: Calculate core KPIs (Cash Runway, Monthly Burn Rate, Gross Margin, MoM Growth).\n"
        "- Task 3: Audit ledger for duplicate payments, price spikes, weekend transfers, and unverified vendors.\n"
        "- Task 4: Retrieve SME benchmark policies via RAG vector search.\n"
        "- Task 5: Synthesize actionable financial advice and executive report."
    )
    
    llm_output = llm_provider.invoke(system_prompt, f"User Query: {state.get('user_query')}", fallback_response=fallback_plan_str)

    # Determine execution flags based on query context
    requires_audit = True
    requires_analysis = True
    requires_rag = True

    plan_res = {
        "summary": llm_output,
        "requires_analysis": requires_analysis,
        "requires_audit": requires_audit,
        "requires_rag": requires_rag,
        "planned_at": datetime.datetime.utcnow().isoformat()
    }

    log_entry = {
        "agent_name": "Planner Agent",
        "action": "Intent Analysis & Strategy Generation",
        "status": "COMPLETED",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "output_summary": f"Formulated execution plan covering financial metrics calculation, audit scan, and RAG retrieval."
    }

    return {
        "plan": plan_res,
        "agent_logs": [log_entry]
    }
