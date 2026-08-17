import os
import sys
import uvicorn

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

if __name__ == "__main__":
    print("Starting AI Financial Analyst & Auditor Application...")
    print("Dashboard available at: http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
