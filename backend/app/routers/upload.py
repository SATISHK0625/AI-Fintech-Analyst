from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.data.ingest import process_uploaded_csv_transactions, process_uploaded_document

router = APIRouter(prefix="/upload", tags=["Data Upload & Live Ingestion"])

@router.post("/transactions")
async def upload_transactions_csv(
    company_id: int = 1,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Dynamically uploads and ingests a CSV transaction ledger file into SQL database."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported for transaction ledgers.")
    
    contents = await file.read()
    result = process_uploaded_csv_transactions(contents, company_id=company_id, db=db)
    return result

@router.post("/document")
async def upload_policy_document(
    file: UploadFile = File(...)
):
    """Dynamically uploads and indexes financial reports/policy documents into RAG vector store."""
    allowed_exts = (".txt", ".md", ".json", ".csv", ".pdf")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail=f"Supported file types: {allowed_exts}")
    
    contents = await file.read()
    result = process_uploaded_document(contents, filename=file.filename)
    return result
