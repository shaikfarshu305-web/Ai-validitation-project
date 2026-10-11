import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db, SessionLocal
from app.services.seed_service import seed_database
from app.rag.ingestion import rebuild_vector_index
from app.api import evaluate, batch, knowledge, analytics, system, report, settings as app_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_validation")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and seed benchmark data
    logger.info("Initializing AI Response Validation SQLite database and vector store...")
    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
        indexed_chunks = rebuild_vector_index(db)
        logger.info("Restored %s knowledge chunks into the vector index.", indexed_chunks)
    finally:
        db.close()
    logger.info("AI Response Validation engine is ready.")
    yield
    logger.info("AI Response Validation backend shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Response Validation & Hallucination Detection System",
    lifespan=lifespan
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(evaluate.router, prefix=settings.API_V1_PREFIX)
app.include_router(batch.router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(system.router, prefix=settings.API_V1_PREFIX)
app.include_router(report.router, prefix=settings.API_V1_PREFIX)
app.include_router(app_settings.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "system": "AI Response Validation System",
        "description": "AI Response Verification & Hallucination Detection System",
        "version": settings.VERSION,
        "status": "ONLINE",
        "endpoints": {
            "evaluate": f"{settings.API_V1_PREFIX}/evaluations",
            "batch": f"{settings.API_V1_PREFIX}/batch",
            "knowledge_base": f"{settings.API_V1_PREFIX}/knowledge-base/stats",
            "analytics": f"{settings.API_V1_PREFIX}/analytics/overview",
            "system_status": f"{settings.API_V1_PREFIX}/system/status",
            "settings": f"{settings.API_V1_PREFIX}/settings"
        }
    }
