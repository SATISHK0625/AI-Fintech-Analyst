import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import AuditFlag, Transaction, Company
from app.agents.analysis import analysis_node
from app.agents.audit import audit_node
from app.agents.retrieval import retrieval_node

router = APIRouter(prefix="/financial", tags=["Financial Dashboard"])

@router.get("/metrics")
def get_financial_metrics(company_id: int = 1, db: Session = Depends(get_db)):
    """Fetches high-level executive financial metrics."""
    state = {"company_id": company_id, "user_query": "Dashboard overview"}
    state = retrieval_node(state)
    state = analysis_node(state)
    return state.get("analysis_results", {})


@router.post("/audit/scan")
def run_live_audit_scan(company_id: int = 1, db: Session = Depends(get_db)):
    """Executes explicit financial audit scan for duplicates, weekend transfers, price surges & unverified vendors."""
    state = {"company_id": company_id, "user_query": "Live audit scan"}
    state = retrieval_node(state)
    state = analysis_node(state)
    state = audit_node(state)

    audit_results = state.get("audit_results", {})
    flags = audit_results.get("flags", [])

    # Persist detected flags into database
    new_flags_added = 0
    for f in flags:
        existing = db.query(AuditFlag).filter(
            AuditFlag.company_id == company_id,
            AuditFlag.title == f["title"],
            AuditFlag.transaction_id == f.get("transaction_id")
        ).first()

        if not existing:
            db_flag = AuditFlag(
                company_id=company_id,
                transaction_id=f.get("transaction_id"),
                flag_type=f["flag_type"],
                severity=f["severity"],
                title=f["title"],
                description=f["description"],
                status="OPEN"
            )
            db.add(db_flag)
            new_flags_added += 1

    if new_flags_added > 0:
        db.commit()

    return {
        "status": "success",
        "total_anomalies": audit_results.get("total_anomalies", 0),
        "high_risk_count": audit_results.get("high_risk_count", 0),
        "medium_risk_count": audit_results.get("medium_risk_count", 0),
        "new_flags_persisted": new_flags_added
    }


@router.get("/anomalies")
def get_audit_anomalies(company_id: int = 1, severity: str = None, db: Session = Depends(get_db)):
    """Fetches audit anomalies and flagged risk transactions."""
    query = db.query(AuditFlag).filter(AuditFlag.company_id == company_id)
    if severity:
        query = query.filter(AuditFlag.severity == severity.upper())
    
    flags = query.order_by(AuditFlag.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "flag_type": f.flag_type,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "status": f.status,
            "transaction_id": f.transaction_id,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for f in flags
    ]


@router.post("/anomalies/{flag_id}/resolve")
def resolve_audit_anomaly(flag_id: int, db: Session = Depends(get_db)):
    """Updates audit flag status to RESOLVED."""
    flag = db.query(AuditFlag).filter(AuditFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Audit flag not found")
    
    flag.status = "RESOLVED"
    db.commit()
    return {"status": "success", "message": f"Audit flag #{flag_id} marked as RESOLVED"}


@router.get("/transactions/export")
def export_transactions_csv(company_id: int = 1, db: Session = Depends(get_db)):
    """Exports current transaction ledger database records as a CSV download."""
    txs = db.query(Transaction).filter(Transaction.company_id == company_id).order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Amount", "Transaction Type", "Category", "Description", "Vendor Name", "Invoice Ref", "Flagged"])

    for t in txs:
        writer.writerow([
            t.date.strftime("%Y-%m-%d") if t.date else "",
            t.amount,
            t.transaction_type,
            t.category,
            t.description,
            t.vendor_name,
            t.invoice_ref,
            "Yes" if t.is_flagged else "No"
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transaction_ledger_export.csv"}
    )
