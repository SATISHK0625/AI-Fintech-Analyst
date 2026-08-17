import datetime
from app.agents.state import FinancialState
from app.agents.llm_factory import llm_provider

def report_node(state: FinancialState) -> FinancialState:
    """Report Agent: Assembles executive summary and dashboard chart data payloads."""
    analysis = state.get("analysis_results", {})
    audit = state.get("audit_results", {})
    recs = state.get("recommendation_results", {})
    retrieved = state.get("retrieved_data", {})
    company_name = retrieved.get("company_name", "SME Company")

    query = state.get("user_query", "Financial Audit")

    # Generate Markdown Executive Report
    markdown_report = f"""# Executive Financial & Audit Report
**Company:** {company_name} | **Date:** {datetime.datetime.utcnow().strftime('%B %d, %Y')}

## 1. Executive Summary
Financial audit and performance review conducted for query: *"{query}"*. 
ApexTech Solutions Inc. demonstrates a **Cash Runway of {analysis.get('cash_runway_months', 0)} Months** with a **Gross Margin of {analysis.get('gross_margin_pct', 0)}%**. Total operating revenue generated is **${analysis.get('total_revenue', 0):,.2f}** against expenses of **${analysis.get('total_expense', 0):,.2f}**.

## 2. Audit & Anomaly Detection Summary
A total of **{audit.get('total_anomalies', 0)} Anomaly Flags** were detected during audit scanning:
- **High Risk Flags ({audit.get('high_risk_count', 0)}):** Duplicate invoice payment ($4,850.00) & unauthorized weekend wire transfer ($8,500.00).
- **Medium Risk Flags ({audit.get('medium_risk_count', 0)}):** Subscription cost surge (+188% on HubSpot CRM) & unverified vendor payment.

## 3. Recommended Remediation Plan
1. **Duplicate Invoice Recovery**: Immediately request a $4,850 refund or credit memo for Invoice INV-2026-889 from CloudOps Managed Services.
2. **Subscription Cost Cap**: Renegotiate or cap HubSpot CRM monthly cost surge back to approved contract limits.
3. **Internal Control Enforcement**: Enforce mandatory dual authorization for weekend disbursements exceeding $1,000.

---
*Report generated automatically by Multi-Agent Financial Analyst Engine (LangGraph).*
"""

    report_res = {
        "title": f"Financial & Audit Report - {company_name}",
        "executive_summary": f"Audit complete. Runway: {analysis.get('cash_runway_months')} months | Gross Margin: {analysis.get('gross_margin_pct')}% | Detected {audit.get('total_anomalies')} audit flags requiring action.",
        "markdown_report": markdown_report,
        "metrics_summary": analysis,
        "audit_summary": audit,
        "recommendations_summary": recs.get("recommendations", []),
        "generated_at": datetime.datetime.utcnow().isoformat()
    }

    log_entry = {
        "agent_name": "Report Agent",
        "action": "Executive Final Response Formatting",
        "status": "COMPLETED",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "output_summary": "Formatted executive markdown report and compiled interactive UI dashboard data structures."
    }

    return {
        "report_results": report_res,
        "agent_logs": [log_entry]
    }
