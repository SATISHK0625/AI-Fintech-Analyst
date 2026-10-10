import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.fintwin_models import FinTwinScenario, FinTwinSimulation
from app.services.fintwin_engine import (
    run_financial_simulation,
    compare_scenarios_against_baseline,
    extract_baseline_financials
)

router = APIRouter(prefix="/fintwin", tags=["FinTwin Financial Decision Simulator"])

# Pydantic Request Models
class ScenarioInputParams(BaseModel):
    revenue_growth_pct: float = Field(0.0, description="Revenue growth or decline percentage (-100 to +500)")
    payroll_expense_change: float = Field(0.0, description="Monthly payroll change delta")
    marketing_expense_change: float = Field(0.0, description="Monthly marketing change delta")
    opex_change: float = Field(0.0, description="Monthly operating expense change delta")
    vendor_payment_delay_days: int = Field(0, ge=0, le=180, description="Vendor payment delay in days")
    capex_one_time: float = Field(0.0, ge=0.0, description="One-time capital expenditure cash outlay")
    duration_months: int = Field(12, ge=1, le=60, description="Simulation timeframe in months")

class CreateScenarioRequest(BaseModel):
    company_id: int = Field(1, description="Authorized Company Tenant ID")
    scenario_name: str = Field(..., min_length=1, max_length=150, description="Scenario name")
    description: Optional[str] = Field(None, max_length=500, description="Scenario description")
    input_parameters: ScenarioInputParams

class UpdateScenarioRequest(BaseModel):
    company_id: int = Field(1, description="Authorized Company Tenant ID")
    scenario_name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    input_parameters: Optional[ScenarioInputParams] = None

class CompareScenariosRequest(BaseModel):
    company_id: int = Field(1, description="Authorized Company Tenant ID")
    scenario_ids: List[int] = Field(..., min_items=1, description="List of scenario IDs to compare")


# API ENDPOINTS

@router.post("/scenarios")
def create_scenario(
    request: CreateScenarioRequest,
    db: Session = Depends(get_db)
):
    """Creates a new FinTwin hypothetical financial scenario for an authorized company workspace."""
    scenario = FinTwinScenario(
        company_id=request.company_id,
        scenario_name=request.scenario_name.strip(),
        description=request.description.strip() if request.description else "",
        input_parameters=json.dumps(request.input_parameters.dict()),
        duration_months=request.input_parameters.duration_months
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "status": "success",
        "message": f"Scenario '{scenario.scenario_name}' created successfully.",
        "scenario": {
            "id": scenario.id,
            "company_id": scenario.company_id,
            "scenario_name": scenario.scenario_name,
            "description": scenario.description,
            "input_parameters": json.loads(scenario.input_parameters),
            "duration_months": scenario.duration_months,
            "created_at": scenario.created_at.strftime("%Y-%m-%d %H:%M")
        }
    }


@router.get("/scenarios")
def list_scenarios(
    company_id: int = Query(1, description="Authorized Company Tenant ID"),
    db: Session = Depends(get_db)
):
    """Lists all saved FinTwin scenarios for the authorized company tenant workspace."""
    scenarios = db.query(FinTwinScenario).filter(
        FinTwinScenario.company_id == company_id
    ).order_by(FinTwinScenario.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "company_id": s.company_id,
            "scenario_name": s.scenario_name,
            "description": s.description,
            "input_parameters": json.loads(s.input_parameters),
            "duration_months": s.duration_months,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else None,
            "simulations_count": len(s.simulations)
        }
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}")
def get_scenario(
    scenario_id: int,
    company_id: int = Query(1, description="Authorized Company Tenant ID"),
    db: Session = Depends(get_db)
):
    """Retrieves a specific FinTwin scenario details for the authorized tenant."""
    scenario = db.query(FinTwinScenario).filter(
        FinTwinScenario.id == scenario_id,
        FinTwinScenario.company_id == company_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="FinTwin scenario not found or access denied.")

    return {
        "id": scenario.id,
        "company_id": scenario.company_id,
        "scenario_name": scenario.scenario_name,
        "description": scenario.description,
        "input_parameters": json.loads(scenario.input_parameters),
        "duration_months": scenario.duration_months,
        "created_at": scenario.created_at.strftime("%Y-%m-%d %H:%M") if scenario.created_at else None
    }


@router.put("/scenarios/{scenario_id}")
def update_scenario(
    scenario_id: int,
    request: UpdateScenarioRequest,
    db: Session = Depends(get_db)
):
    """Updates an existing FinTwin scenario parameters for the authorized company workspace."""
    scenario = db.query(FinTwinScenario).filter(
        FinTwinScenario.id == scenario_id,
        FinTwinScenario.company_id == request.company_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="FinTwin scenario not found or access denied.")

    if request.scenario_name:
        scenario.scenario_name = request.scenario_name.strip()
    if request.description is not None:
        scenario.description = request.description.strip()
    if request.input_parameters:
        scenario.input_parameters = json.dumps(request.input_parameters.dict())
        scenario.duration_months = request.input_parameters.duration_months

    db.commit()
    db.refresh(scenario)

    return {
        "status": "success",
        "message": f"Scenario #{scenario_id} updated successfully.",
        "scenario": {
            "id": scenario.id,
            "company_id": scenario.company_id,
            "scenario_name": scenario.scenario_name,
            "description": scenario.description,
            "input_parameters": json.loads(scenario.input_parameters),
            "duration_months": scenario.duration_months,
            "updated_at": scenario.updated_at.strftime("%Y-%m-%d %H:%M") if scenario.updated_at else None
        }
    }


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    company_id: int = Query(1, description="Authorized Company Tenant ID"),
    db: Session = Depends(get_db)
):
    """Deletes a FinTwin scenario and its associated simulation runs for the authorized workspace."""
    scenario = db.query(FinTwinScenario).filter(
        FinTwinScenario.id == scenario_id,
        FinTwinScenario.company_id == company_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="FinTwin scenario not found or access denied.")

    db.delete(scenario)
    db.commit()

    return {
        "status": "success",
        "message": f"Scenario #{scenario_id} deleted successfully."
    }


@router.post("/scenarios/{scenario_id}/simulate")
def run_scenario_simulation(
    scenario_id: int,
    company_id: int = Query(1, description="Authorized Company Tenant ID"),
    db: Session = Depends(get_db)
):
    """
    Runs a financial simulation for a scenario against the current company baseline data,
    persisting the simulation results in FinTwinSimulation without modifying the ledger.
    """
    scenario = db.query(FinTwinScenario).filter(
        FinTwinScenario.id == scenario_id,
        FinTwinScenario.company_id == company_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="FinTwin scenario not found or access denied.")

    params = json.loads(scenario.input_parameters)
    sim_result = run_financial_simulation(db=db, company_id=company_id, input_params=params)

    if sim_result.get("status") == "error":
        raise HTTPException(status_code=400, detail=sim_result.get("message"))

    # Save simulation run record
    simulation_record = FinTwinSimulation(
        scenario_id=scenario.id,
        baseline_snapshot=json.dumps(sim_result["baseline"]),
        projected_results=json.dumps(sim_result["projected_results"]),
        risk_assessment=json.dumps(sim_result["risk_assessment"]),
        assumptions=json.dumps(sim_result["assumptions"])
    )
    db.add(simulation_record)
    db.commit()
    db.refresh(simulation_record)

    return {
        "status": "success",
        "simulation_id": simulation_record.id,
        "scenario_id": scenario.id,
        "scenario_name": scenario.scenario_name,
        "simulation_results": sim_result
    }


@router.get("/scenarios/{scenario_id}/simulations")
def get_scenario_simulations(
    scenario_id: int,
    company_id: int = Query(1, description="Authorized Company Tenant ID"),
    db: Session = Depends(get_db)
):
    """Retrieves simulation execution history for a FinTwin scenario."""
    scenario = db.query(FinTwinScenario).filter(
        FinTwinScenario.id == scenario_id,
        FinTwinScenario.company_id == company_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="FinTwin scenario not found or access denied.")

    sims = db.query(FinTwinSimulation).filter(
        FinTwinSimulation.scenario_id == scenario_id
    ).order_by(FinTwinSimulation.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "scenario_id": s.scenario_id,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else None,
            "baseline_snapshot": json.loads(s.baseline_snapshot),
            "projected_results": json.loads(s.projected_results),
            "risk_assessment": json.loads(s.risk_assessment),
            "assumptions": json.loads(s.assumptions)
        }
        for s in sims
    ]


@router.post("/compare")
def compare_scenarios(
    request: CompareScenariosRequest,
    db: Session = Depends(get_db)
):
    """
    Compares multiple authorized scenarios for a company workspace against a consistent baseline.
    """
    scenarios = db.query(FinTwinScenario).filter(
        FinTwinScenario.id.in_(request.scenario_ids),
        FinTwinScenario.company_id == request.company_id
    ).all()

    if not scenarios:
        raise HTTPException(status_code=404, detail="No matching scenarios found for comparison.")

    simulations_to_compare = []
    for sc in scenarios:
        params = json.loads(sc.input_parameters)
        res = run_financial_simulation(db=db, company_id=request.company_id, input_params=params)
        if res.get("status") == "success":
            simulations_to_compare.append({
                "scenario_id": sc.id,
                "scenario_name": sc.scenario_name,
                "projected_results": res["projected_results"],
                "risk_assessment": res["risk_assessment"]
            })

    comparison_result = compare_scenarios_against_baseline(
        db=db,
        company_id=request.company_id,
        simulations_list=simulations_to_compare
    )

    return comparison_result
