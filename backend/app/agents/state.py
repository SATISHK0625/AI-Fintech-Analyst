import operator
from typing import TypedDict, List, Dict, Any, Optional, Annotated

class AgentStepLog(TypedDict):
    agent_name: str
    action: str
    status: str
    timestamp: str
    output_summary: str

class FinancialState(TypedDict):
    user_query: str
    company_id: int
    plan: Optional[Dict[str, Any]]
    retrieved_data: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    audit_results: Optional[Dict[str, Any]]
    recommendation_results: Optional[Dict[str, Any]]
    report_results: Optional[Dict[str, Any]]
    agent_logs: Annotated[List[AgentStepLog], operator.add]
    error: Optional[str]
