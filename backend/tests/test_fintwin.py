import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models import Company, Transaction
from app.database.fintwin_models import FinTwinScenario, FinTwinSimulation
from app.services.fintwin_engine import (
    extract_baseline_financials,
    validate_scenario_params,
    run_financial_simulation,
    evaluate_scenario_risks,
    compare_scenarios_against_baseline
)

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


def test_baseline_extraction_and_ledger_immutability(db_session):
    """Verifies baseline extraction works and ledger records remain untouched."""
    company = db_session.query(Company).filter(Company.id == 1).first()
    assert company is not None

    initial_tx_count = db_session.query(Transaction).filter(Transaction.company_id == 1).count()
    assert initial_tx_count > 0

    baseline = extract_baseline_financials(db_session, company_id=1)
    assert baseline["has_baseline"] is True
    assert baseline["total_revenue"] > 0
    assert baseline["total_expense"] > 0
    assert baseline["cash_runway_months"] > 0

    # Ensure transaction count didn't change
    after_tx_count = db_session.query(Transaction).filter(Transaction.company_id == 1).count()
    assert initial_tx_count == after_tx_count


def test_validate_scenario_params():
    """Validates boundary conditions and defaults for scenario params."""
    params = validate_scenario_params({
        "revenue_growth_pct": "25.5",
        "duration_months": 120, # should be capped at 60
        "capex_one_time": -500 # should be non-negative
    })
    assert params["revenue_growth_pct"] == 25.5
    assert params["duration_months"] == 60
    assert params["capex_one_time"] == 0.0


def test_simulation_engine_growth_scenario(db_session):
    """Tests growth scenario with positive revenue and payroll changes."""
    input_params = {
        "revenue_growth_pct": 80.0,
        "payroll_expense_change": 2000.0,
        "marketing_expense_change": 1000.0,
        "opex_change": -500.0,
        "vendor_payment_delay_days": 0,
        "capex_one_time": 0.0,
        "duration_months": 6
    }

    result = run_financial_simulation(db_session, company_id=1, input_params=input_params)
    assert result["status"] == "success"
    assert "projected_results" in result
    proj = result["projected_results"]
    assert proj["duration_months"] == 6
    assert len(proj["monthly_breakdown"]) == 6
    assert proj["ending_cash"] > 0
    assert "deltas" in proj
    assert "cash_runway_months" in proj
    assert len(result["assumptions"]) > 0


def test_simulation_engine_insolvency_scenario(db_session):
    """Tests scenario where high expenses deplete cash reserves (insolvency detection)."""
    input_params = {
        "revenue_growth_pct": -50.0,
        "payroll_expense_change": 150000.0, # extremely high burn
        "marketing_expense_change": 50000.0,
        "opex_change": 50000.0,
        "vendor_payment_delay_days": 0,
        "capex_one_time": 400000.0,
        "duration_months": 12
    }

    result = run_financial_simulation(db_session, company_id=1, input_params=input_params)
    assert result["status"] == "success"
    proj = result["projected_results"]
    assert proj["insolvent_month"] is not None
    assert proj["ending_cash"] == 0.0

    risk = result["risk_assessment"]
    assert risk["overall_risk_level"] == "HIGH"
    risk_codes = [f["code"] for f in risk["risk_flags"]]
    assert "CASH_INSOLVENCY_RISK" in risk_codes


def test_scenario_comparison(db_session):
    """Tests side-by-side comparison matrix generation."""
    sims = [
        {
            "scenario_id": 1,
            "scenario_name": "Conservative",
            "projected_results": {
                "duration_months": 12,
                "total_revenue": 500000.0,
                "total_expense": 400000.0,
                "net_cash_flow": 100000.0,
                "ending_cash": 600000.0,
                "cash_runway_months": 36.0,
                "profit_margin_pct": 20.0,
                "deltas": {"runway_months_delta": 5.0}
            },
            "risk_assessment": {"risk_score": 10, "overall_risk_level": "LOW"}
        },
        {
            "scenario_id": 2,
            "scenario_name": "Aggressive",
            "projected_results": {
                "duration_months": 12,
                "total_revenue": 700000.0,
                "total_expense": 800000.0,
                "net_cash_flow": -100000.0,
                "ending_cash": 400000.0,
                "cash_runway_months": 10.0,
                "profit_margin_pct": -14.2,
                "deltas": {"runway_months_delta": -21.0}
            },
            "risk_assessment": {"risk_score": 45, "overall_risk_level": "HIGH"}
        }
    ]

    comp = compare_scenarios_against_baseline(db_session, company_id=1, simulations_list=sims)
    assert comp["status"] == "success"
    assert comp["scenarios_count"] == 2
    assert len(comp["comparison"]) == 2


def test_api_crud_and_simulation_lifecycle(db_session):
    """Full API lifecycle: Create scenario, simulate, list, compare, and delete."""
    # 1. Create scenario
    create_payload = {
        "company_id": 1,
        "scenario_name": "Pytest Expansion Scenario",
        "description": "Integration test scenario created by pytest",
        "input_parameters": {
            "revenue_growth_pct": 15.0,
            "payroll_expense_change": 8000.0,
            "marketing_expense_change": 3000.0,
            "opex_change": 1000.0,
            "vendor_payment_delay_days": 30,
            "capex_one_time": 10000.0,
            "duration_months": 12
        }
    }

    res = client.post("/api/fintwin/scenarios", json=create_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    scenario_id = data["scenario"]["id"]
    assert scenario_id > 0

    # 2. Get scenario
    get_res = client.get(f"/api/fintwin/scenarios/{scenario_id}?company_id=1")
    assert get_res.status_code == 200
    assert get_res.json()["scenario_name"] == "Pytest Expansion Scenario"

    # 3. Run simulation endpoint
    sim_res = client.post(f"/api/fintwin/scenarios/{scenario_id}/simulate?company_id=1")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "success"
    assert "simulation_results" in sim_data
    assert sim_data["simulation_results"]["projected_results"]["cash_runway_months"] > 0

    # 4. Get simulations history
    hist_res = client.get(f"/api/fintwin/scenarios/{scenario_id}/simulations?company_id=1")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1

    # 5. Compare scenarios endpoint
    comp_res = client.post("/api/fintwin/compare", json={
        "company_id": 1,
        "scenario_ids": [scenario_id]
    })
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "success"
    assert len(comp_data["comparison"]) == 1

    # 6. Tenant Isolation check: Company 2 cannot access this scenario
    tenant_res = client.get(f"/api/fintwin/scenarios/{scenario_id}?company_id=999")
    assert tenant_res.status_code == 404

    # 7. Delete scenario
    del_res = client.delete(f"/api/fintwin/scenarios/{scenario_id}?company_id=1")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify deleted
    verify_del = client.get(f"/api/fintwin/scenarios/{scenario_id}?company_id=1")
    assert verify_del.status_code == 404
