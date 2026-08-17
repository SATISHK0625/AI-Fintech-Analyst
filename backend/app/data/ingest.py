import io
import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.database.models import Transaction, Account
from app.rag.vector_store import vector_store

def process_uploaded_csv_transactions(file_bytes: bytes, company_id: int, db: Session) -> dict:
    """Parses uploaded CSV file and inserts transactions into database."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    
    # Standardize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    
    # Required columns mapping flexibility
    date_col = next((c for c in df.columns if "date" in c), "date")
    amount_col = next((c for c in df.columns if "amount" in c or "cost" in c or "price" in c), "amount")
    desc_col = next((c for c in df.columns if "description" in c or "desc" in c or "title" in c), "description")
    vendor_col = next((c for c in df.columns if "vendor" in c or "payee" in c or "merchant" in c), "vendor_name")
    type_col = next((c for c in df.columns if "type" in c or "category" in c), "transaction_type")
    cat_col = next((c for c in df.columns if "category" in c), "category")
    invoice_col = next((c for c in df.columns if "invoice" in c or "ref" in c), "invoice_ref")

    added_count = 0
    new_transactions = []

    for _, row in df.iterrows():
        try:
            tx_date = pd.to_datetime(row.get(date_col, datetime.datetime.utcnow())).to_pydatetime()
            amount = abs(float(row.get(amount_col, 0.0)))
            tx_type = str(row.get(type_col, "Debit"))
            if "credit" in tx_type.lower() or "income" in tx_type.lower() or "revenue" in tx_type.lower():
                t_type = "Credit"
            else:
                t_type = "Debit"
                
            category = str(row.get(cat_col, "General Expense"))
            desc = str(row.get(desc_col, "Uploaded Transaction"))
            vendor = str(row.get(vendor_col, "Unknown Vendor"))
            inv_ref = str(row.get(invoice_col, "")) if pd.notna(row.get(invoice_col)) else None

            tx = Transaction(
                company_id=company_id,
                date=tx_date,
                amount=amount,
                transaction_type=t_type,
                category=category,
                description=desc,
                vendor_name=vendor,
                invoice_ref=inv_ref
            )
            new_transactions.append(tx)
            added_count += 1
        except Exception as e:
            continue

    if new_transactions:
        db.add_all(new_transactions)
        db.commit()

    return {"status": "success", "added_transactions": added_count}


def process_uploaded_document(file_bytes: bytes, filename: str) -> dict:
    """Processes uploaded TXT or document content into RAG vector store chunks."""
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = str(file_bytes)

    # Chunking strategy: 500 characters with 100 character overlap
    chunk_size = 500
    overlap = 100
    chunks = []
    
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)

    if not chunks:
        chunks = [text[:1000]]

    indexed_count = vector_store.add_custom_documents(text_chunks=chunks, source_name=filename)
    return {"status": "success", "filename": filename, "indexed_chunks": indexed_count}
