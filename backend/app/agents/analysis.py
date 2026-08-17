import datetime
import pandas as pd
from app.agents.state import FinancialState

def analysis_node(state: FinancialState) -> FinancialState:
    """Analysis Agent: Performs quantitative financial health & metric calculations."""
    retrieved = state.get("retrieved_data", {})
    transactions = retrieved.get("transactions", [])

    if not transactions:
        state["analysis_results"] = {
            "total_revenue": 0.0,
            "total_expense": 0.0,
            "net_cash_flow": 0.0,
            "burn_rate": 0.0,
            "cash_runway_months": 0.0,
            "gross_margin_pct": 0.0
        }
        return state

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)

    # 1. Total Revenue and Expenses
    revenue_df = df[df["type"] == "Credit"]
    expense_df = df[df["type"] == "Debit"]

    total_revenue = float(revenue_df["amount"].sum())
    total_expense = float(expense_df["amount"].sum())
    net_cash_flow = total_revenue - total_expense

    # 2. Monthly Aggregations
    df["year_month"] = df["date"].dt.to_period("M")
    monthly_rev = df[df["type"] == "Credit"].groupby("year_month")["amount"].sum()
    monthly_exp = df[df["type"] == "Debit"].groupby("year_month")["amount"].sum()

    num_months = max(len(monthly_exp), 1)
    avg_monthly_rev = total_revenue / num_months
    avg_monthly_exp = total_expense / num_months

    # Monthly Net Burn Rate = Expenses - Revenue (if operating at deficit)
    net_burn_rate = max(0.0, avg_monthly_exp - avg_monthly_rev)

    # Estimated Current Cash Reserve (Starting balance of $500,000 + Net Cash Flow)
    assumed_starting_cash = 500000.0
    current_estimated_cash = max(0.0, assumed_starting_cash + net_cash_flow)

    cash_runway_months = (
        round(current_estimated_cash / net_burn_rate, 1)
        if net_burn_rate > 0
        else 36.0 # Highly sustainable if positive cashflow
    )

    # Gross Margin %
    # Direct Cost of Sales (Cloud hosting + Contractors) vs Revenue
    cogs_categories = ["Cloud Hosting", "Consulting", "Subcontractors"]
    cogs_amount = float(df[(df["type"] == "Debit") & (df["category"].isin(cogs_categories))]["amount"].sum())
    
    gross_margin_pct = (
        round(((total_revenue - cogs_amount) / total_revenue) * 100, 1)
        if total_revenue > 0
        else 0.0
    )

    # Category Expense Breakdown
    cat_breakdown = df[df["type"] == "Debit"].groupby("category")["amount"].sum().to_dict()
    category_expenses = {k: round(float(v), 2) for k, v in cat_breakdown.items()}

    # Recent Monthly Trend Data for Charts
    recent_months = []
    all_months = sorted(list(set(monthly_rev.index).union(set(monthly_exp.index))))
    for m in all_months[-6:]: # Last 6 months
        rev = float(monthly_rev.get(m, 0.0))
        exp = float(monthly_exp.get(m, 0.0))
        recent_months.append({
            "month": str(m),
            "revenue": round(rev, 2),
            "expense": round(exp, 2),
            "net": round(rev - exp, 2)
        })

    analysis_res = {
        "total_revenue": round(total_revenue, 2),
        "total_expense": round(total_expense, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "avg_monthly_rev": round(avg_monthly_rev, 2),
        "avg_monthly_exp": round(avg_monthly_exp, 2),
        "net_burn_rate": round(net_burn_rate, 2),
        "estimated_cash": round(current_estimated_cash, 2),
        "cash_runway_months": cash_runway_months,
        "gross_margin_pct": gross_margin_pct,
        "category_expenses": category_expenses,
        "monthly_trend": recent_months,
        "calculated_at": datetime.datetime.utcnow().isoformat()
    }

    log_entry = {
        "agent_name": "Analysis Agent",
        "action": "Financial Health & Ratio Analysis",
        "status": "COMPLETED",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "output_summary": f"Calculated Revenue (${total_revenue:,.2f}), Expenses (${total_expense:,.2f}), Runway ({cash_runway_months} mos), Gross Margin ({gross_margin_pct}%)."
    }

    return {
        "analysis_results": analysis_res,
        "agent_logs": [log_entry]
    }
