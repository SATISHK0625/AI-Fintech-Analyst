# 🛡️ FinAuditor Enterprise
### Autonomous Multi-Agent AI Financial Analyst & Forensic Audit Suite

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![Framework](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)
![Multi--Agent](https://img.shields.io/badge/Orchestration-LangGraph-purple.svg)
![VectorDB](https://img.shields.io/badge/VectorStore-ChromaDB-orange.svg)

FinAuditor Enterprise is an autonomous, multi-tenant AI financial intelligence engine designed for SME executives, CFOs, and audit teams. It combines **quantitative financial ledger analysis**, **rule-based and AI-powered forensic anomaly detection**, **RAG-based policy document retrieval**, and a **LangGraph multi-agent state machine** to deliver real-time financial health monitoring and executive audit reports.

---

## ✨ Key Features

- 📊 **Real-Time Financial Dashboard**: Instant metrics for estimated Cash Runway (months), Monthly Net Burn Rate, Gross Margin %, and Category Expense breakdowns.
- 🛡️ **Forensic Audit & Anomaly Detection**: Automated scan engine detecting:
  - **Duplicate Invoice Overpayments** (e.g., identical charges across different dates).
  - **Off-Hours Weekend Wire Transfers** (unauthorized non-business day disbursements).
  - **Subscription Cost Spikes** (SaaS price surges > 50%).
  - **Unverified & Suspicious Vendors** (missing W-9 tax compliance).
- 🧠 **ChromaDB Vector RAG Policy Search**: Context-aware retrieval over enterprise financial control handbooks, compliance policies, and expense rules embedded locally via `sentence-transformers/all-MiniLM-L6-v2`.
- 🤖 **LangGraph Multi-Agent Engine**: Modular sequential state machine orchestrating 6 specialized agents:
  1. **Planner Agent**: Formulates execution strategy.
  2. **Retrieval Agent**: Fetches SQL ledgers and vector embeddings.
  3. **Analysis Agent**: Computes Pandas quantitative ratios & runway projections.
  4. **Audit Agent**: Audits ledger entries for risk anomalies.
  5. **Recommendation Agent**: Formulates remediation action items.
  6. **Report Agent**: Synthesizes structured executive audit memos.
- 💬 **Conversational AI Console**: Interactive, human-like chat assistant grounded in actual company financial ledgers and policy RAG context.
- 🏢 **Multi-Tenant Enterprise Portal**: High-converting authentication portal featuring company workspace registration, custom CSV ledger ingestion, and policy document upload.

---

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.10+, SQLAlchemy (SQLite), LangGraph, LangChain, ChromaDB, SentenceTransformers, Pandas, Pytest.
- **Frontend**: HTML5, Vanilla CSS3 (Enterprise Glassmorphism Design Token System), JavaScript ES6+, Chart.js, Marked.js, FontAwesome 6.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed on your system.
- **Git** installed.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd "Financial Analyst"
```

### 2. Create & Activate a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

*(Optional: Set your custom `LLM_API_KEY` in `.env` if using OpenAI API mode; otherwise, the built-in intelligent synthesis engine runs locally without any API keys).*

### 4. Run the Application Server

```bash
python run.py
```

The application will start on **`http://localhost:8000`**.

### 5. Access the Web Dashboard

Open your web browser and navigate to:
```text
http://localhost:8000
```

---

## 🧪 Running Automated Tests

To run the full backend unit test suite (database seeding, vector RAG search, and LangGraph multi-agent workflow):

```bash
pytest backend/tests/test_engine.py
```

---

## 📁 Project Architecture

```text
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph Multi-Agent Nodes (Planner, Retrieval, Analysis, Audit, etc.)
│   │   ├── data/            # SQL seed scripts, sample CSV ledgers & markdown policy handbooks
│   │   ├── database/        # SQLAlchemy Models & SQLite session setup
│   │   ├── rag/             # ChromaDB Persistent Vector Store Manager
│   │   ├── routers/         # FastAPI Routers (Auth, Financial, Agent Chat, Ingestion)
│   │   ├── config.py        # Environment Configuration
│   │   └── main.py          # FastAPI Application Core
│   └── tests/               # Pytest Suite
├── frontend/
│   ├── css/                 # Enterprise Dark Glassmorphism CSS Design Token System
│   ├── js/                  # Vanilla ES6 Modules (app.js, charts.js, upload.js)
│   └── index.html           # Main Application Dashboard & Auth Landing Screen
├── run.py                   # Uvicorn Server Launch Entrypoint
└── README.md                # Project Documentation
```

---

## 📄 License

This project is open-source and available under the **MIT License**.
