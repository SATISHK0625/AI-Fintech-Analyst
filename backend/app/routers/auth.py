import hashlib
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import User, Company, Account, Vendor, Subscription, AuditFlag
from app.rag.vector_store import vector_store
from app.data.ingest import process_uploaded_csv_transactions, process_uploaded_document

router = APIRouter(prefix="/auth", tags=["User Authentication & Multi-Tenancy"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: str
    industry: Optional[str] = "Technology & Services"

@router.post("/register")
async def register_user(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    company_name: str = Form(...),
    industry: str = Form("Technology & Operations"),
    csv_file: Optional[UploadFile] = File(None),
    policy_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Registers a new user, creates their company account, and ingests optional CSV ledger & policy document."""
    email_clean = email.strip().lower()
    if not email_clean or not password.strip():
        raise HTTPException(status_code=400, detail="Email and password are required")

    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    # 1. Create or Find Company
    company = db.query(Company).filter(Company.name == company_name.strip()).first()
    if not company:
        company = Company(
            name=company_name.strip(),
            industry=industry.strip() if industry else "General Business",
            created_at=datetime.datetime.utcnow()
        )
        db.add(company)
        db.flush()

        # Seed basic accounts
        rev_acc = Account(company_id=company.id, account_code="4000", account_name="Operating Revenue", account_type="Revenue")
        exp_acc = Account(company_id=company.id, account_code="5000", account_name="Operating Expense", account_type="Expense")
        db.add_all([rev_acc, exp_acc])
        db.flush()

    # 2. Create User
    user = User(
        company_id=company.id,
        email=email_clean,
        password_hash=hash_password(password.strip()),
        full_name=full_name.strip()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 3. Process optional uploaded CSV ledger
    csv_summary = "No CSV uploaded"
    if csv_file and csv_file.filename:
        content = await csv_file.read()
        res = process_uploaded_csv_transactions(file_bytes=content, company_id=company.id, db=db)
        csv_summary = f"Ingested {res.get('added_transactions', 0)} transactions"

        # Scan for audit anomalies on uploaded ledger
        from app.agents.audit import scan_and_save_audit_flags
        scan_and_save_audit_flags(db, company.id)

    # 4. Process optional uploaded policy document into RAG
    policy_summary = "No policy document uploaded"
    if policy_file and policy_file.filename:
        content = await policy_file.read()
        res = process_uploaded_document(file_bytes=content, filename=policy_file.filename)
        # Tag vector chunks with company_id
        text_chunks = res.get("chunks", [])
        if text_chunks:
            vector_store.add_custom_documents(text_chunks, source_name=policy_file.filename, company_id=company.id)
        policy_summary = f"Indexed {res.get('indexed_chunks', 0)} chunks into ChromaDB"

    return {
        "status": "success",
        "message": "User and Company registered successfully!",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company_id": company.id,
            "company_name": company.name,
            "industry": company.industry
        },
        "csv_summary": csv_summary,
        "policy_summary": policy_summary
    }

@router.post("/login")
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns active company profile."""
    email_clean = request.email.strip().lower()
    hashed = hash_password(request.password.strip())

    user = db.query(User).filter(User.email == email_clean, User.password_hash == hashed).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    company = db.query(Company).filter(Company.id == user.company_id).first()

    return {
        "status": "success",
        "message": "Authenticated successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company_id": user.company_id,
            "company_name": company.name if company else "SME Company",
            "industry": company.industry if company else "Technology"
        }
    }

@router.get("/companies")
def get_public_companies(db: Session = Depends(get_db)):
    """Returns a list of all registered companies for quick selector switching."""
    companies = db.query(Company).order_by(Company.id.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "industry": c.industry
        }
        for c in companies
    ]
