import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database.session import init_db, SessionLocal
from app.data.seed_data import load_initial_ledger_data
from app.rag.vector_store import vector_store
from app.routers import financial, upload, agent, auth, fintwin

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(financial.router, prefix=settings.API_V1_STR)
app.include_router(upload.router, prefix=settings.API_V1_STR)
app.include_router(agent.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(fintwin.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_event():
    """Initializes database tables, seeds initial dataset from CSV & RAG vector store."""
    init_db()
    db = SessionLocal()
    try:
        load_initial_ledger_data(db)
    finally:
        db.close()
    
    vector_store.seed_initial_knowledge()

# Frontend Static File Serving
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def read_root():
        return FileResponse(
            os.path.join(frontend_path, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}
