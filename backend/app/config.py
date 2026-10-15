import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# Load .env from root or backend directory
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Response Validation System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Storage & DB
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_URL: str = os.getenv("DATABASE_URL") or f"sqlite:///{Path(__file__).resolve().parent.parent / 'proofraq.db'}"
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")  # local, openai, gemini, anthropic
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    
    # Vector DB & Embeddings
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "faiss")  # faiss, memory
    VECTOR_INDEX_DIR: Path = BASE_DIR / "vector_indices"
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "300"))
    DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    DEFAULT_RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "4"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))
    
    # Evaluation Weights (Must sum to 1.0)
    DEFAULT_WEIGHT_ACCURACY: float = 0.30
    DEFAULT_WEIGHT_HALLUCINATION: float = 0.25
    DEFAULT_WEIGHT_RELEVANCE: float = 0.25
    DEFAULT_WEIGHT_COMPLETENESS: float = 0.20
    
    # Verdict Thresholds
    DEFAULT_THRESHOLD_PASS: float = 70.0
    DEFAULT_THRESHOLD_NEEDS_IMPROVEMENT: float = 60.0
    
    # Hallucination Sensitivity: "low", "standard", "high"
    HALLUCINATION_SENSITIVITY: str = os.getenv("HALLUCINATION_SENSITIVITY", "standard")
    SEED_DEMO_EVALUATIONS: bool = os.getenv("SEED_DEMO_EVALUATIONS", "false").lower() == "true"

settings = Settings()
os.makedirs(settings.VECTOR_INDEX_DIR, exist_ok=True)


def migrate_legacy_default_weights(settings_data: Dict[str, Any]) -> Dict[str, Any]:
    legacy_defaults = (
        {
            "weight_accuracy": 0.35,
            "weight_hallucination": 0.30,
            "weight_relevance": 0.20,
            "weight_completeness": 0.15,
        },
        {
            "weight_accuracy": 0.35,
            "weight_hallucination": 0.20,
            "weight_relevance": 0.25,
            "weight_completeness": 0.20,
        },
        {
            "weight_accuracy": 0.35,
            "weight_hallucination": 0.25,
            "weight_relevance": 0.25,
            "weight_completeness": 0.15,
        },
    )
    if not all(key in settings_data for key in legacy_defaults[0]):
        return settings_data
    try:
        is_legacy_default = any(
            all(abs(float(settings_data[key]) - value) < 0.0001 for key, value in old.items())
            for old in legacy_defaults
        )
    except (TypeError, ValueError):
        return settings_data
    if not is_legacy_default:
        return settings_data

    migrated = dict(settings_data)
    migrated.update({
        "weight_accuracy": settings.DEFAULT_WEIGHT_ACCURACY,
        "weight_hallucination": settings.DEFAULT_WEIGHT_HALLUCINATION,
        "weight_relevance": settings.DEFAULT_WEIGHT_RELEVANCE,
        "weight_completeness": settings.DEFAULT_WEIGHT_COMPLETENESS,
    })
    return migrated
