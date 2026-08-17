import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.models import AuditFlag, Transaction, Subscription, Vendor
from app.agents.state import FinancialState

def audit_node(state: FinancialState) -> FinancialState:
    """Audit Agent: Detects duplicate invoices, anomalous wire transfers, and subscription spikes."""
    retrieved = state.get("retrieved_data", {})
    transactions = retrieved.get("transactions", [])
    subscriptions = retrieved.get("subscriptions", [])
    vendors = retrieved.get("vendors", [])
    company_id = state.get("company_id", 1)

    detected_flags = []

    # 1. Check for Duplicate Payments
    seen_invoices = {}
    for tx in transactions:
        inv = tx.get("invoice_ref")
        vendor = tx.get("vendor_name")
        amount = tx.get("amount")
        if inv and inv.strip():
            key = f"{vendor}_{inv}_{amount}"
            if key in seen_invoices:
                prev_tx = seen_invoices[key]
                detected_flags.append({
                    "flag_type": "DUPLICATE_PAYMENT",
                    "severity": "HIGH",
                    "title": "Duplicate Invoice Payment Detected",
                    "description": f"Identical payment of ${amount:,.2f} to '{vendor}' with Invoice Ref '{inv}' processed multiple times (TX #{prev_tx['id']} and TX #{tx['id']}).",
                    "transaction_id": tx["id"]
                })
            else:
                seen_invoices[key] = tx

    # 2. Check for Weekend / Off-Hours Wire Transfers (> $1,000)
    for tx in transactions:
        tx_date = datetime.datetime.strptime(tx["date"], "%Y-%m-%d")
        amount = tx.get("amount", 0.0)
        vendor = tx.get("vendor_name", "")
        if tx_date.weekday() >= 5 and amount > 1000.0: # Saturday/Sunday
            detected_flags.append({
                "flag_type": "WEEKEND_TRANSFER",
                "severity": "HIGH",
                "title": "Off-Hours Weekend Disbursement",
                "description": f"Disbursement of ${amount:,.2f} to vendor '{vendor}' was executed on a {tx_date.strftime('%A')} ({tx['date']}). Requires authorization review.",
                "transaction_id": tx["id"]
            })

    # 3. Check for Subscription Price Surges (> 15% increase)
    for sub in subscriptions:
        current_cost = sub.get("monthly_cost", 0.0)
        prev_cost = sub.get("previous_cost")
        vendor = sub.get("vendor", "")
        if prev_cost and prev_cost > 0:
            increase_pct = ((current_cost - prev_cost) / prev_cost) * 100
            if increase_pct > 15.0:
                detected_flags.append({
                    "flag_type": "PRICE_SURGE",
                    "severity": "MEDIUM",
                    "title": "Subscription Cost Spike",
                    "description": f"Monthly cost for subscription '{vendor}' increased by {increase_pct:.1f}% (from ${prev_cost:,.2f} to ${current_cost:,.2f}).",
                    "transaction_id": None
                })

    # 4. Check for Unverified Vendors
    unverified_vendor_names = {v["name"] for v in vendors if v["status"] in ["Unverified", "Suspicious"]}
    for tx in transactions:
        vendor = tx.get("vendor_name")
        amount = tx.get("amount", 0.0)
        if vendor in unverified_vendor_names and amount > 500.0:
            detected_flags.append({
                "flag_type": "UNVERIFIED_VENDOR",
                "severity": "MEDIUM",
                "title": "Unverified Vendor Payment",
                "description": f"Payment of ${amount:,.2f} made to vendor '{vendor}' which is flagged as unverified in master records.",
                "transaction_id": tx["id"]
            })

    # Fetch any existing audit flags from DB to combine
    db: Session = SessionLocal()
    try:
        db_flags = db.query(AuditFlag).filter(AuditFlag.company_id == company_id).all()
        for df in db_flags:
            # Avoid duplicate reporting
            if not any(f["title"] == df.title for f in detected_flags):
                detected_flags.append({
                    "flag_type": df.flag_type,
                    "severity": df.severity,
                    "title": df.title,
                    "description": df.description,
                    "transaction_id": df.transaction_id
                })
    finally:
        db.close()

    high_risk_count = sum(1 for f in detected_flags if f["severity"] == "HIGH")
    medium_risk_count = sum(1 for f in detected_flags if f["severity"] == "MEDIUM")

    audit_res = {
        "total_anomalies": len(detected_flags),
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "flags": detected_flags,
        "audited_at": datetime.datetime.utcnow().isoformat()
    }

    log_entry = {
        "agent_name": "Audit Agent",
        "action": "Financial Anomaly & Risk Audit Scan",
        "status": "COMPLETED",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "output_summary": f"Detected {len(detected_flags)} anomalies ({high_risk_count} High Risk, {medium_risk_count} Medium Risk)."
    }

    return {
        "audit_results": audit_res,
        "agent_logs": [log_entry]
    }


def scan_and_save_audit_flags(db: Session, company_id: int):
    """Scans all company transactions for anomalies and persists AuditFlags into DB."""
    txs = db.query(Transaction).filter(Transaction.company_id == company_id).all()
    if not txs:
        return

    # Check for Duplicate Payments
    seen_invoices = {}
    for tx in txs:
        if tx.invoice_ref and tx.invoice_ref.strip():
            key = f"{tx.vendor_name}_{tx.invoice_ref}_{tx.amount}"
            if key in seen_invoices:
                af = AuditFlag(
                    company_id=company_id,
                    transaction_id=tx.id,
                    flag_type="DUPLICATE_PAYMENT",
                    severity="HIGH",
                    title="Duplicate Invoice Payment Detected",
                    description=f"Identical payment of ${tx.amount:,.2f} to '{tx.vendor_name}' with Invoice Ref '{tx.invoice_ref}' processed multiple times.",
                    status="OPEN"
                )
                db.add(af)
            else:
                seen_invoices[key] = tx

        # Weekend transfers
        if tx.date and tx.date.weekday() in (5, 6) and tx.amount >= 1000:
            af = AuditFlag(
                company_id=company_id,
                transaction_id=tx.id,
                flag_type="WEEKEND_TRANSFER",
                severity="HIGH",
                title="Off-Hours Weekend Wire Transfer",
                description=f"Payment of ${tx.amount:,.2f} to '{tx.vendor_name}' executed on weekend ({tx.date.strftime('%A')}).",
                status="OPEN"
            )
            db.add(af)

        # Unverified vendors
        if tx.vendor_name and "unverified" in tx.vendor_name.lower():
            af = AuditFlag(
                company_id=company_id,
                transaction_id=tx.id,
                flag_type="UNVERIFIED_VENDOR",
                severity="MEDIUM",
                title="Payment to Unverified Vendor",
                description=f"Payment of ${tx.amount:,.2f} to unverified vendor '{tx.vendor_name}'.",
                status="OPEN"
            )
            db.add(af)

    db.commit()

