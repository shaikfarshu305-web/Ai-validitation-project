from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import SystemSettings
from app.schemas.evaluation_schemas import SettingsSchema, SettingsUpdate
from app.config import migrate_legacy_default_weights, settings

router = APIRouter(prefix="/settings", tags=["Settings"])

DEFAULT_SETTINGS = {
    "llm_provider": "local",
    "model": "Local NLP & Semantic Analyzer",
    "temperature": 0.2,
    "weight_accuracy": 0.30,
    "weight_hallucination": 0.25,
    "weight_relevance": 0.25,
    "weight_completeness": 0.20,
    "threshold_pass": 75.0,
    "threshold_needs_improvement": 50.0,
    "retrieval_top_k": 4,
    "chunk_size": 300,
    "chunk_overlap": 50,
    "hallucination_sensitivity": "standard"
}

@router.get("", response_model=SettingsSchema)
def get_system_settings(db: Session = Depends(get_db)):
    """Retrieve active system configuration parameters."""
    rec = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not rec:
        rec = SystemSettings(id=1, settings_json=DEFAULT_SETTINGS, updated_at=datetime.utcnow())
        db.add(rec)
        db.commit()
        db.refresh(rec)
    current_settings = migrate_legacy_default_weights(rec.settings_json)
    if current_settings != rec.settings_json:
        rec.settings_json = current_settings
        rec.updated_at = datetime.utcnow()
        db.commit()
    return SettingsSchema(**current_settings)

@router.put("", response_model=SettingsSchema)
def update_system_settings(update_data: SettingsUpdate, db: Session = Depends(get_db)):
    """Update configurable weights, thresholds, and RAG retrieval settings."""
    rec = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    current = migrate_legacy_default_weights(rec.settings_json) if rec else DEFAULT_SETTINGS.copy()

    # Validate weights if updated
    w_acc = update_data.weight_accuracy if update_data.weight_accuracy is not None else current["weight_accuracy"]
    w_hal = update_data.weight_hallucination if update_data.weight_hallucination is not None else current["weight_hallucination"]
    w_rel = update_data.weight_relevance if update_data.weight_relevance is not None else current["weight_relevance"]
    w_com = update_data.weight_completeness if update_data.weight_completeness is not None else current["weight_completeness"]

    total_w = w_acc + w_hal + w_rel + w_com
    if abs(total_w - 1.0) > 0.05:
        # Normalize weights automatically to sum to 1.0
        w_acc, w_hal, w_rel, w_com = w_acc/total_w, w_hal/total_w, w_rel/total_w, w_com/total_w

    update_dict = update_data.model_dump(exclude_unset=True)
    current.update(update_dict)
    current["weight_accuracy"] = round(w_acc, 2)
    current["weight_hallucination"] = round(w_hal, 2)
    current["weight_relevance"] = round(w_rel, 2)
    current["weight_completeness"] = round(w_com, 2)

    if not rec:
        rec = SystemSettings(id=1, settings_json=current, updated_at=datetime.utcnow())
        db.add(rec)
    else:
        rec.settings_json = current
        rec.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rec)
    return SettingsSchema(**rec.settings_json)

@router.post("/reset", response_model=SettingsSchema)
def reset_system_settings(db: Session = Depends(get_db)):
    """Reset all parameters to default certified settings."""
    rec = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not rec:
        rec = SystemSettings(id=1, settings_json=DEFAULT_SETTINGS, updated_at=datetime.utcnow())
        db.add(rec)
    else:
        rec.settings_json = DEFAULT_SETTINGS.copy()
        rec.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return SettingsSchema(**rec.settings_json)
