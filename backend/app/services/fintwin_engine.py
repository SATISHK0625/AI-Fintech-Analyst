import datetime
import pandas as pd
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database.models import Transaction
from app.rag.vector_store import vector_store

def extract_baseline_financials(db: Session, company_id: int) -> Dict[str, Any]:
    """
    Extracts baseline financial metrics from existing company transactions without modifying any database records.
    """
    txs = db.query(Transaction).filter(Transaction.company_id == company_id).all()
    if not txs:
        return {
            "has_baseline": False,
            "message": "No transaction ledger data found for this company. Please upload financial transactions to establish a baseline.",
            "total_revenue": 0.0,
            "total_expense": 0.0,
            "net_cash_flow": 0.0,
            "avg_monthly_rev": 0.0,
            "avg_monthly_exp": 0.0,
            "net_burn_rate": 0.0,
            "estimated_cash": 0.0,
            "cash_runway_months": 0.0,
            "gross_margin_pct": 0.0
        }

    records = []
    for t in txs:
        records.append({
            "date": t.date,
            "amount": float(t.amount),
            "type": t.transaction_type,
            "category": t.category
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])

    total_revenue = float(df[df["type"] == "Credit"]["amount"].sum())
    total_expense = float(df[df["type"] == "Debit"]["amount"].sum())
    net_cash_flow = total_revenue - total_expense

    df["year_month"] = df["date"].dt.to_period("M")
    monthly_exp = df[df["type"] == "Debit"].groupby("year_month")["amount"].sum()
    num_months = max(len(monthly_exp), 1)

    avg_monthly_rev = total_revenue / num_months
    avg_monthly_exp = total_expense / num_months
    net_burn_rate = max(0.0, avg_monthly_exp - avg_monthly_rev)

    assumed_starting_cash = 500000.0
    estimated_cash = max(0.0, assumed_starting_cash + net_cash_flow)

    cash_runway_months = (
        round(estimated_cash / net_burn_rate, 1)
        if net_burn_rate > 0
        else 60.0
    )

    cogs_categories = ["Cloud Hosting", "Consulting", "Subcontractors"]
    cogs_amount = float(df[(df["type"] == "Debit") & (df["category"].isin(cogs_categories))]["amount"].sum())
    gross_margin_pct = (
        round(((total_revenue - cogs_amount) / total_revenue) * 100, 1)
        if total_revenue > 0
        else 0.0
    )

    return {
        "has_baseline": True,
        "company_id": company_id,
        "total_revenue": round(total_revenue, 2),
        "total_expense": round(total_expense, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "avg_monthly_rev": round(avg_monthly_rev, 2),
        "avg_monthly_exp": round(avg_monthly_exp, 2),
        "net_burn_rate": round(net_burn_rate, 2),
        "estimated_cash": round(estimated_cash, 2),
        "cash_runway_months": cash_runway_months,
        "gross_margin_pct": gross_margin_pct,
        "num_historical_months": num_months
    }


def validate_scenario_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validates user-submitted scenario inputs and sets safe defaults."""
    clean_params = {
        "revenue_growth_pct": float(params.get("revenue_growth_pct", 0.0)),
        "payroll_expense_change": float(params.get("payroll_expense_change", 0.0)),
        "marketing_expense_change": float(params.get("marketing_expense_change", 0.0)),
        "opex_change": float(params.get("opex_change", 0.0)),
        "vendor_payment_delay_days": int(params.get("vendor_payment_delay_days", 0)),
        "capex_one_time": max(0.0, float(params.get("capex_one_time", 0.0))),
        "duration_months": max(1, min(60, int(params.get("duration_months", 12))))
    }
    return clean_params


def run_financial_simulation(
    db: Session,
    company_id: int,
    input_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes a deterministic financial simulation using company baseline data without mutating the database.
    """
    baseline = extract_baseline_financials(db, company_id)
    if not baseline.get("has_baseline"):
        return {
            "status": "error",
            "message": baseline.get("message"),
            "baseline": baseline,
            "projections": None,
            "risk_assessment": None
        }

    params = validate_scenario_params(input_params)
    duration = params["duration_months"]
    rev_growth_pct = params["revenue_growth_pct"]
    payroll_change = params["payroll_expense_change"]
    mktg_change = params["marketing_expense_change"]
    opex_change = params["opex_change"]
    delay_days = params["vendor_payment_delay_days"]
    capex = params["capex_one_time"]

    start_cash = baseline["estimated_cash"]
    base_monthly_rev = baseline["avg_monthly_rev"]
    base_monthly_exp = baseline["avg_monthly_exp"]

    monthly_projections = []
    current_cash = start_cash
    insolvent_month = None

    total_proj_rev = 0.0
    total_proj_exp = 0.0

    # Vendor delay deferral logic (25% deferred from M1 to M2 if delay >= 30 days)
    deferred_vendor_amount = 0.0
    if delay_days >= 30:
        deferred_vendor_amount = base_monthly_exp * 0.25

    for m in range(1, duration + 1):
        # Linear monthly growth applied to revenue
        monthly_rev = base_monthly_rev * (1.0 + (rev_growth_pct / 100.0) * (m / 12.0))
        monthly_rev = max(0.0, monthly_rev)

        # Baseline operating expense + adjustments
        monthly_exp = base_monthly_exp + payroll_change + mktg_change + opex_change

        # Month 1 adjustments
        if m == 1:
            if capex > 0:
                monthly_exp += capex
            if deferred_vendor_amount > 0:
                monthly_exp -= deferred_vendor_amount
        elif m == 2 and deferred_vendor_amount > 0:
            monthly_exp += deferred_vendor_amount

        monthly_exp = max(0.0, monthly_exp)

        monthly_net = monthly_rev - monthly_exp
        current_cash += monthly_net

        if current_cash <= 0 and insolvent_month is None:
            insolvent_month = m

        total_proj_rev += monthly_rev
        total_proj_exp += monthly_exp

        monthly_projections.append({
            "month": m,
            "revenue": round(monthly_rev, 2),
            "expense": round(monthly_exp, 2),
            "net_cash_flow": round(monthly_net, 2),
            "ending_cash": round(max(0.0, current_cash), 2),
            "is_insolvent": current_cash <= 0
        })

    ending_cash = max(0.0, current_cash)
    proj_net_cash_flow = total_proj_rev - total_proj_exp
    proj_net_burn_rate = abs(proj_net_cash_flow) / duration if proj_net_cash_flow < 0 else 0.0

    if insolvent_month is not None:
        proj_runway_months = float(insolvent_month)
    elif proj_net_burn_rate > 0:
        proj_runway_months = round(ending_cash / proj_net_burn_rate, 1)
    else:
        proj_runway_months = 60.0

    proj_net_income = total_proj_rev - total_proj_exp
    proj_profit_margin = (
        round((proj_net_income / total_proj_rev) * 100, 1)
        if total_proj_rev > 0
        else 0.0
    )

    # Deltas relative to baseline
    baseline_runway = baseline["cash_runway_months"]
    runway_delta = round(proj_runway_months - baseline_runway, 1)
    ending_cash_delta = round(ending_cash - start_cash, 2)
    net_cash_flow_delta = round(proj_net_cash_flow - (baseline["net_cash_flow"] * (duration / 12)), 2)

    projections_summary = {
        "duration_months": duration,
        "total_revenue": round(total_proj_rev, 2),
        "total_expense": round(total_proj_exp, 2),
        "net_cash_flow": round(proj_net_cash_flow, 2),
        "ending_cash": ending_cash,
        "net_burn_rate": round(proj_net_burn_rate, 2),
        "cash_runway_months": proj_runway_months,
        "net_income": round(proj_net_income, 2),
        "profit_margin_pct": proj_profit_margin,
        "insolvent_month": insolvent_month,
        "deltas": {
            "runway_months_delta": runway_delta,
            "ending_cash_delta": ending_cash_delta,
            "net_cash_flow_delta": net_cash_flow_delta
        },
        "monthly_breakdown": monthly_projections
    }

    # Documented Assumptions
    assumptions = [
        f"Baseline opening cash reserve estimated at ${start_cash:,.2f}.",
        f"Revenue growth rate of {rev_growth_pct}% applied progressively across {duration} months.",
        f"Payroll monthly delta of ${payroll_change:+,} and marketing delta of ${mktg_change:+,}.",
        f"OpEx monthly delta of ${opex_change:+,}.",
        "Distinguishes cash accounting flow from accrual profit.",
        "Projections represent deterministic model estimates based on current baseline data and user inputs."
    ]
    if capex > 0:
        assumptions.append(f"One-time CapEx cash outlay of ${capex:,.2f} applied in Month 1.")
    if delay_days >= 30:
        assumptions.append(f"Vendor payment delay of {delay_days} days defers 25% of Month 1 expense outflow into Month 2.")

    # Perform Risk Assessment & Policy Evidence Search
    risk_assessment = evaluate_scenario_risks(
        baseline=baseline,
        projections=projections_summary,
        input_params=params
    )

    return {
        "status": "success",
        "baseline": baseline,
        "input_parameters": params,
        "projected_results": projections_summary,
        "assumptions": assumptions,
        "risk_assessment": risk_assessment,
        "simulated_at": datetime.datetime.utcnow().isoformat()
    }


def evaluate_scenario_risks(
    baseline: Dict[str, Any],
    projections: Dict[str, Any],
    input_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates scenario projections for financial risks and queries ChromaDB RAG for compliance policy rules.
    """
    flags = []
    score = 0 # 0 (Safe) to 100 (High Risk)

    insolvent_month = projections.get("insolvent_month")
    ending_cash = projections.get("ending_cash", 0.0)
    runway_months = projections.get("cash_runway_months", 0.0)
    net_cash_flow = projections.get("net_cash_flow", 0.0)
    profit_margin = projections.get("profit_margin_pct", 0.0)
    capex = input_params.get("capex_one_time", 0.0)
    delay_days = input_params.get("vendor_payment_delay_days", 0)

    # Risk 1: Cash Insolvency
    if insolvent_month is not None:
        flags.append({
            "code": "CASH_INSOLVENCY_RISK",
            "severity": "HIGH",
            "title": f"Cash Insolvency Depletion in Month {insolvent_month}",
            "description": f"Under this scenario, company cash reserves will be completely exhausted in Month {insolvent_month}."
        })
        score += 50
    elif runway_months < 6.0:
        flags.append({
            "code": "CRITICAL_RUNWAY_SHRINKAGE",
            "severity": "HIGH",
            "title": f"Critically Low Cash Runway ({runway_months} months)",
            "description": "Estimated runway drops below the recommended 6-month enterprise safety reserve threshold."
        })
        score += 30
    elif runway_months < 12.0:
        flags.append({
            "code": "MODERATE_RUNWAY_SHRINKAGE",
            "severity": "MEDIUM",
            "title": f"Shortened Cash Runway ({runway_months} months)",
            "description": "Runway is below 12 months, requiring careful expense monitoring."
        })
        score += 15

    # Risk 2: Unsustainable Net Cash Drain
    if net_cash_flow < 0:
        flags.append({
            "code": "NET_CASH_DRAIN",
            "severity": "MEDIUM",
            "title": f"Net Deficit Cash Outflow (${abs(net_cash_flow):,.2f})",
            "description": "Operating expenses exceed projected revenues over the scenario timeframe."
        })
        score += 20

    # Risk 3: Declining Profit Margin
    if profit_margin < 0:
        flags.append({
            "code": "NEGATIVE_PROFIT_MARGIN",
            "severity": "MEDIUM",
            "title": f"Negative Net Profit Margin ({profit_margin}%)",
            "description": "Operating expenses outweigh revenues, resulting in negative profitability."
        })
        score += 15

    # Risk 4: Large CapEx Outflow
    if capex > (baseline.get("estimated_cash", 1.0) * 0.3):
        flags.append({
            "code": "HIGH_CAPEX_EXPOSURE",
            "severity": "MEDIUM",
            "title": f"Significant One-Time CapEx (${capex:,.2f})",
            "description": "One-time capital expenditure consumes over 30% of current liquid cash reserves."
        })
        score += 15

    # Risk 5: Vendor Delay Cash Deferral Shock
    if delay_days >= 60:
        flags.append({
            "code": "VENDOR_PAYMENT_DEFERRAL_RISK",
            "severity": "LOW",
            "title": f"Extended Vendor Payment Delay ({delay_days} days)",
            "description": "Deferring vendor payments creates a cumulative cash outflow cliff in subsequent months."
        })
        score += 10

    overall_level = "LOW"
    if score >= 45:
        overall_level = "HIGH"
    elif score >= 20:
        overall_level = "MEDIUM"

    # Search ChromaDB Vector Store for RAG Policy Evidence
    rag_policy_evidence = []
    try:
        query_text = "cash runway policy expenditure capital reserve"
        rag_res = vector_store.search_knowledge_base(query_text, n_results=2)
        for r in rag_res:
            rag_policy_evidence.append({
                "source": r.get("source", "Enterprise Policy Handbook"),
                "content": r.get("content", "")[:300] + "..."
            })
    except Exception as e:
        rag_policy_evidence.append({
            "source": "Default SME Compliance Standard",
            "content": "Enterprise cash management standard mandates minimum 6 months operating cash runway buffer."
        })

    # AI Actionable Recommendations
    recommendations = []
    if insolvent_month is not None:
        recommendations.append(f"Immediate Action: Reduce monthly payroll or OpEx delta to extend cash reserves beyond Month {insolvent_month}.")
    if capex > 0:
        recommendations.append(f"CapEx Planning: Consider financing the ${capex:,.2f} capital expenditure over 24-36 months to protect liquid cash reserves.")
    if input_params.get("revenue_growth_pct", 0) <= 0 and net_cash_flow < 0:
        recommendations.append("Growth Target: Model targeted marketing investments to offset operating expense growth with incremental revenue.")
    if not recommendations:
        recommendations.append("Financial Structure: Projections maintain a healthy cash reserve. Monitor monthly actuals against scenario benchmarks.")

    return {
        "risk_score": min(100, score),
        "overall_risk_level": overall_level,
        "risk_flags": flags,
        "policy_evidence": rag_policy_evidence,
        "recommendations": recommendations,
        "disclaimer": "Projections and risk indicators are mathematical models based on inputs and historical data. AI commentary is for executive reference."
    }


def compare_scenarios_against_baseline(
    db: Session,
    company_id: int,
    simulations_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compares multiple scenario simulations against a common company baseline.
    """
    baseline = extract_baseline_financials(db, company_id)

    comparison_matrix = []
    for sim in simulations_list:
        name = sim.get("scenario_name", "Scenario")
        scen_id = sim.get("scenario_id")
        proj = sim.get("projected_results", {})
        risk = sim.get("risk_assessment", {})

        comparison_matrix.append({
            "scenario_id": scen_id,
            "scenario_name": name,
            "duration_months": proj.get("duration_months", 12),
            "total_revenue": proj.get("total_revenue", 0.0),
            "total_expense": proj.get("total_expense", 0.0),
            "net_cash_flow": proj.get("net_cash_flow", 0.0),
            "ending_cash": proj.get("ending_cash", 0.0),
            "cash_runway_months": proj.get("cash_runway_months", 0.0),
            "profit_margin_pct": proj.get("profit_margin_pct", 0.0),
            "risk_score": risk.get("risk_score", 0),
            "overall_risk_level": risk.get("overall_risk_level", "LOW"),
            "deltas": proj.get("deltas", {})
        })

    return {
        "status": "success",
        "baseline": baseline,
        "scenarios_count": len(comparison_matrix),
        "comparison": comparison_matrix,
        "compared_at": datetime.datetime.utcnow().isoformat()
    }
