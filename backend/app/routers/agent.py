import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import SavedReport, ChatMessage
from app.data.seed_data import load_initial_ledger_data
from app.rag.vector_store import vector_store
from app.agents.graph import run_financial_agent_workflow
from app.agents.conversational import generate_chat_response
from app.agents.llm_factory import llm_provider

router = APIRouter(prefix="/agent", tags=["LangGraph & Conversational AI Engine"])

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    company_id: int = 1

class ReportRequest(BaseModel):
    query: str = "Executive Financial Audit & Performance Review"
    company_id: int = 1


@router.get("/telemetry")
def get_llm_telemetry():
    """Returns LLM token usage, execution latency, and estimated cost telemetry."""
    return llm_provider.get_telemetry_summary()


@router.post("/chat")
def handle_chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    """Handles natural language chat interaction with session persistence."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = request.session_id if request.session_id and request.session_id.strip() else f"chat_{uuid.uuid4().hex[:8]}"

    # Save User Message
    user_msg = ChatMessage(
        company_id=request.company_id,
        session_id=session_id,
        sender="user",
        message=request.query.strip()
    )
    db.add(user_msg)
    db.commit()

    # Fetch recent messages in active session for contextual awareness
    session_msgs_db = (
        db.query(ChatMessage)
        .filter(ChatMessage.company_id == request.company_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    session_messages = [{"sender": m.sender, "message": m.message} for m in session_msgs_db]

    # Generate conversational AI response
    response_text = generate_chat_response(
        query=request.query.strip(),
        session_messages=session_messages,
        company_id=request.company_id
    )

    # Save Assistant Response
    agent_msg = ChatMessage(
        company_id=request.company_id,
        session_id=session_id,
        sender="agent",
        agent_name="FinAuditor Assistant",
        message=response_text
    )
    db.add(agent_msg)
    db.commit()

    return {
        "status": "success",
        "session_id": session_id,
        "query": request.query.strip(),
        "response": response_text
    }


@router.get("/sessions")
def get_chat_sessions(company_id: int = 1, db: Session = Depends(get_db)):
    """Returns a list of saved chat sessions with initial snippet and timestamp."""
    subquery = (
        db.query(
            ChatMessage.session_id,
            func.min(ChatMessage.id).label("min_id"),
            func.max(ChatMessage.created_at).label("last_active")
        )
        .filter(ChatMessage.company_id == company_id)
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    results = (
        db.query(subquery.c.session_id, subquery.c.last_active, ChatMessage.message)
        .join(ChatMessage, ChatMessage.id == subquery.c.min_id)
        .order_by(subquery.c.last_active.desc())
        .all()
    )

    sessions = []
    for s_id, last_active, first_msg in results:
        snippet = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
        sessions.append({
            "session_id": s_id,
            "title": snippet,
            "last_active": last_active.strftime("%Y-%m-%d %H:%M")
        })

    return sessions


@router.get("/sessions/{session_id}")
def get_session_messages(session_id: str, company_id: int = 1, db: Session = Depends(get_db)):
    """Returns all messages belonging to a specific chat session."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.company_id == company_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "sender": m.sender,
            "agent_name": m.agent_name,
            "message": m.message,
            "created_at": m.created_at.strftime("%H:%M")
        }
        for m in messages
    ]


@router.post("/generate-report")
def generate_executive_report(request: ReportRequest, db: Session = Depends(get_db)):
    """Explicitly executes the full multi-agent workflow graph to produce and save an Executive Report."""
    query = request.query.strip() if request.query and request.query.strip() else "Executive Financial & Audit Review"
    result = run_financial_agent_workflow(user_query=query, company_id=request.company_id)

    report_data = result.get("report_results", {})
    audit_data = result.get("audit_results", {})

    saved_report = SavedReport(
        company_id=request.company_id,
        query_text=query,
        title=report_data.get("title", "Executive Financial & Audit Report"),
        executive_summary=report_data.get("executive_summary", "Multi-agent report generated."),
        markdown_report=report_data.get("markdown_report", ""),
        anomalies_count=audit_data.get("total_anomalies", 0)
    )
    db.add(saved_report)
    db.commit()
    db.refresh(saved_report)

    return {
        "status": "success",
        "report_id": saved_report.id,
        "title": saved_report.title,
        "executive_summary": saved_report.executive_summary,
        "markdown_report": saved_report.markdown_report,
        "created_at": saved_report.created_at.strftime("%Y-%m-%d %H:%M")
    }


@router.get("/reports")
def get_saved_reports(company_id: int = 1, db: Session = Depends(get_db)):
    """Returns a list of all historically generated audit & financial reports."""
    reports = db.query(SavedReport).filter(SavedReport.company_id == company_id).order_by(SavedReport.created_at.desc()).all()
    return reports


@router.get("/reports/{report_id}")
def get_report_by_id(report_id: int, db: Session = Depends(get_db)):
    """Returns details of a specific saved report."""
    report = db.query(SavedReport).filter(SavedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    """Seeds the database directly from transaction_ledger.csv and indexes Enterprise Policy RAG Knowledge Base."""
    company_id = load_initial_ledger_data(db)
    vector_store.seed_initial_knowledge()
    return {"status": "success", "message": "Enterprise Financial Dataset & Vector RAG Knowledge Base successfully initialized!", "company_id": company_id}
