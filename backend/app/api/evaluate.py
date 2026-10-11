import asyncio
import json
from typing import List, Optional, AsyncIterator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.session import get_db
from app.models.db_models import (
    EvaluationSubmission,
    EvaluationResult,
    AgentEvaluation,
    EvaluationHistory,
    SystemSettings,
)
from app.schemas.evaluation_schemas import (
    SingleEvaluationRequest,
    EvaluationDetailResponse,
    EvaluationListItem,
)
from app.orchestrator.evaluation_orchestrator import orchestrator
from app.config import migrate_legacy_default_weights

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


def _get_weights_thresholds(db: Session):
    """Load custom weights/thresholds from DB settings."""
    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    weights = thresholds = None
    if sys_settings and sys_settings.settings_json:
        s = migrate_legacy_default_weights(sys_settings.settings_json)
        weights = {
            "accuracy": s.get("weight_accuracy", 0.35),
            "hallucination": s.get("weight_hallucination", 0.25),
            "relevance": s.get("weight_relevance", 0.25),
            "completeness": s.get("weight_completeness", 0.15),
        }
        thresholds = {
            "pass": s.get("threshold_pass", 75.0),
            "needs_improvement": s.get("threshold_needs_improvement", 50.0),
        }
    return weights, thresholds


# ── Standard evaluation endpoint ────────────────────────────────────────────

@router.post("", response_model=EvaluationDetailResponse)
def evaluate_response(req: SingleEvaluationRequest, db: Session = Depends(get_db)):
    """
    Execute single AI response verification (parallel agents, single DB commit).
    The helper is intentionally synchronous so the same function can be called in
    tests and by FastAPI without requiring an async caller.
    """
    if not req.question.strip() or not req.ai_response.strip():
        raise HTTPException(status_code=400, detail="Question and AI Response are required.")

    weights, thresholds = _get_weights_thresholds(db)
    try:
        result = asyncio.run(
            orchestrator.run_evaluation_async(
                db, req, custom_weights=weights, custom_thresholds=thresholds
            )
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# ── SSE streaming evaluation endpoint ────────────────────────────────────────

@router.post("/stream")
async def evaluate_response_stream(
    req: SingleEvaluationRequest, db: Session = Depends(get_db)
):
    """
    Server-Sent Events endpoint — streams real progress updates during evaluation.
    Frontend receives stage updates as the pipeline runs.

    Event format: data: {"stage": "...", "status": "...", "detail": "..."}
    Final event:  data: {"stage": "result", "status": "complete", "result": {...}}
    """
    if not req.question.strip() or not req.ai_response.strip():
        raise HTTPException(status_code=400, detail="Question and AI Response are required.")

    weights, thresholds = _get_weights_thresholds(db)

    # Shared queue between the evaluation coroutine and the SSE generator
    queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(stage: str, status: str, detail: str = ""):
        await queue.put({"stage": stage, "status": status, "detail": detail})

    async def run_eval():
        try:
            result = await orchestrator.run_evaluation_async(
                db, req, custom_weights=weights, custom_thresholds=thresholds,
                progress_callback=progress_callback,
            )
            # Serialize retrieved_evidence (Pydantic objects → dicts)
            result_copy = dict(result)
            if result_copy.get("retrieved_evidence"):
                result_copy["retrieved_evidence"] = [
                    e.model_dump() if hasattr(e, "model_dump") else e
                    for e in result_copy["retrieved_evidence"]
                ]
            await queue.put({"stage": "result", "status": "complete", "result": result_copy})
        except Exception as e:
            await queue.put({"stage": "error", "status": "failed", "detail": str(e)})
        finally:
            await queue.put(None)  # Sentinel — signals end of stream

    async def event_generator() -> AsyncIterator[str]:
        # Start evaluation in background
        asyncio.create_task(run_eval())

        while True:
            msg = await asyncio.wait_for(queue.get(), timeout=120.0)
            if msg is None:
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── List evaluations ─────────────────────────────────────────────────────────

@router.get("", response_model=List[EvaluationListItem])
def list_evaluations(
    search: Optional[str] = None,
    verdict: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    hallucination_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = (
        db.query(EvaluationSubmission, EvaluationResult, EvaluationHistory)
        .join(EvaluationResult, EvaluationSubmission.id == EvaluationResult.evaluation_id)
        .join(EvaluationHistory, EvaluationSubmission.id == EvaluationHistory.evaluation_id)
    )

    if search:
        query = query.filter(EvaluationSubmission.question.ilike(f"%{search.strip()}%"))
    if verdict and verdict.strip().upper() != "ALL":
        query = query.filter(EvaluationResult.verdict == verdict.strip().upper())
    if min_score is not None:
        query = query.filter(EvaluationResult.overall_score >= min_score)
    if max_score is not None:
        query = query.filter(EvaluationResult.overall_score <= max_score)
    if hallucination_status and hallucination_status.strip().upper() != "ALL":
        query = query.filter(EvaluationHistory.hallucination_status == hallucination_status.strip().upper())

    records = query.order_by(desc(EvaluationSubmission.created_at)).offset(offset).limit(limit).all()

    return [
        EvaluationListItem(
            id=sub.id,
            question=sub.question,
            overall_score=res.overall_score,
            accuracy=res.accuracy_score,
            relevance=res.relevance_score,
            hallucination=res.hallucination_score,
            completeness=res.completeness_score,
            verdict=res.verdict,
            hallucination_status=hist.hallucination_status,
            created_at=sub.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        for sub, res, hist in records
    ]


# ── Get evaluation detail ─────────────────────────────────────────────────────

@router.get("/{eval_id}", response_model=EvaluationDetailResponse)
def get_evaluation_detail(eval_id: str, db: Session = Depends(get_db)):
    submission = db.query(EvaluationSubmission).filter(EvaluationSubmission.id == eval_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Evaluation submission not found.")

    result = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == eval_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Evaluation result record not found.")

    raw = result.raw_metrics or {}

    return EvaluationDetailResponse(
        id=submission.id,
        question=submission.question,
        ai_response=submission.ai_response,
        reference_answer=submission.reference_answer,
        source_information=submission.source_information,
        created_at=submission.created_at.isoformat(),
        status=submission.status,
        relevance_score=result.relevance_score,
        accuracy_score=result.accuracy_score,
        hallucination_score=result.hallucination_score,
        hallucination_percentage=(raw.get("verdict") or {}).get("dimension_scores", {}).get("hallucination_percentage", 0.0),
        completeness_score=result.completeness_score,
        overall_score=result.overall_score,
        verdict=result.verdict,
        summary=result.summary,
        major_issues=result.major_issues or [],
        recommendations=result.recommendations or [],
        relevance_details=raw.get("relevance"),
        accuracy_details=raw.get("accuracy"),
        hallucination_details=raw.get("hallucination"),
        completeness_details=raw.get("completeness"),
        verdict_details=raw.get("verdict"),
        retrieved_evidence=result.retrieved_evidence or [],
    )


@router.delete("/{eval_id}")
def delete_evaluation(eval_id: str, db: Session = Depends(get_db)):
    submission = db.query(EvaluationSubmission).filter(EvaluationSubmission.id == eval_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    db.delete(submission)
    db.commit()
    return {"message": f"Evaluation {eval_id} deleted successfully."}
