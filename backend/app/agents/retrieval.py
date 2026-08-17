import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.models import Transaction, Company, Account, Vendor, Subscription
from app.rag.vector_store import vector_store
from app.agents.state import FinancialState

def retrieval_node(state: FinancialState) -> FinancialState:
    """Retrieval Agent: Fetches structured financial records and RAG vector store snippets."""
    company_id = state.get("company_id", 1)
    query = state.get("user_query", "")

    db: Session = SessionLocal()
    try:
        # 1. Fetch Company Info
        company = db.query(Company).filter(Company.id == company_id).first()
        company_name = company.name if company else "SME Company"

        # 2. Fetch Structured Database Transactions
        transactions = db.query(Transaction).filter(Transaction.company_id == company_id).order_by(Transaction.date.desc()).all()
        
        tx_list = []
        for t in transactions:
            tx_list.append({
                "id": t.id,
                "date": t.date.strftime("%Y-%m-%d"),
                "amount": t.amount,
                "type": t.transaction_type,
                "category": t.category,
                "description": t.description,
                "vendor_name": t.vendor_name,
                "invoice_ref": t.invoice_ref,
                "is_flagged": t.is_flagged,
                "flag_reason": t.flag_reason
            })

        # 3. Fetch Subscriptions and Vendors
        subs = db.query(Subscription).filter(Subscription.company_id == company_id).all()
        subs_list = [
            {
                "vendor": s.vendor_name,
                "monthly_cost": s.monthly_cost,
                "previous_cost": s.previous_cost,
                "status": s.status
            }
            for s in subs
        ]

        vendors = db.query(Vendor).filter(Vendor.company_id == company_id).all()
        vendor_list = [{"name": v.name, "category": v.category, "status": v.status} for v in vendors]

        # 4. Perform RAG Vector Store Search
        rag_results = vector_store.search_knowledge_base(query=query, n_results=4)

        retrieved_res = {
            "company_name": company_name,
            "total_transactions": len(tx_list),
            "transactions": tx_list,
            "subscriptions": subs_list,
            "vendors": vendor_list,
            "rag_context": rag_results,
            "retrieved_at": datetime.datetime.utcnow().isoformat()
        }

        log_entry = {
            "agent_name": "Retrieval Agent",
            "action": "Hybrid SQL & Vector RAG Retrieval",
            "status": "COMPLETED",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "output_summary": f"Fetched {len(tx_list)} ledger transactions, {len(subs_list)} subscription records, and {len(rag_results)} RAG policy snippets."
        }

        return {
            "retrieved_data": retrieved_res,
            "agent_logs": [log_entry]
        }
    finally:
        db.close()
