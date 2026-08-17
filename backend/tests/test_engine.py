import os
import sys
# Standard library imports

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import init_db, SessionLocal
from app.database.models import Company, Transaction, AuditFlag
from app.data.seed_data import load_initial_ledger_data
from app.rag.vector_store import vector_store
from app.agents.graph import run_financial_agent_workflow
from app.agents.analysis import analysis_node
from app.agents.retrieval import retrieval_node
from app.data.ingest import process_uploaded_document

def test_database_and_seed_data():
    init_db()
    db = SessionLocal()
    try:
        company_id = load_initial_ledger_data(db)
        assert company_id > 0

        company = db.query(Company).filter(Company.id == company_id).first()
        assert company is not None
        assert company.name == "ApexTech Solutions Inc."

        tx_count = db.query(Transaction).filter(Transaction.company_id == company_id).count()
        assert tx_count > 10

        flags_count = db.query(AuditFlag).filter(AuditFlag.company_id == company_id).count()
        assert flags_count >= 3
    finally:
        db.close()

def test_rag_vector_store():
    vector_store.seed_initial_knowledge()
    results = vector_store.search_knowledge_base("SaaS Gross Margin benchmark", n_results=2)
    assert len(results) > 0
    assert "SaaS" in results[0]["content"] or "Gross Margin" in results[0]["content"]

    # Test dynamic document indexing
    ingest_res = process_uploaded_document(b"Company Audit Policy: All expense claims above $500 require receipt upload.", "policy.txt")
    assert ingest_res["status"] == "success"
    assert ingest_res["indexed_chunks"] > 0

def test_langgraph_multi_agent_workflow():
    db = SessionLocal()
    try:
        company_id = load_initial_ledger_data(db)
    finally:
        db.close()

    query = "Audit transaction ledger for duplicate invoice payments and calculate cash runway"
    final_state = run_financial_agent_workflow(user_query=query, company_id=company_id)

    assert final_state["plan"] is not None
    assert final_state["retrieved_data"] is not None
    assert final_state["analysis_results"] is not None
    assert final_state["audit_results"] is not None
    assert final_state["recommendation_results"] is not None
    assert final_state["report_results"] is not None

    # Check metrics
    analysis = final_state["analysis_results"]
    assert analysis["cash_runway_months"] > 0
    assert analysis["total_revenue"] > 0

    # Check audit anomalies detected
    audit = final_state["audit_results"]
    assert audit["total_anomalies"] >= 3
    assert any(f["flag_type"] == "DUPLICATE_PAYMENT" for f in audit["flags"])

    # Check agent execution logs
    logs = final_state["agent_logs"]
    assert len(logs) == 6 # Planner, Retrieval, Analysis, Audit, Recommendation, Report
