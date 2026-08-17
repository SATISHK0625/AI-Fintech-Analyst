import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_PATH = os.path.join(ROOT_DIR, "financial_analyst.db").replace("\\", "/")
DEFAULT_CHROMA_DIR = os.path.join(ROOT_DIR, "chroma_db").replace("\\", "/")

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Financial Analyst & Auditor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

    # LLM Settings (Supports custom Base URL, strict rate limits optimization)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    # RAG Vector Store
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", DEFAULT_CHROMA_DIR)
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

