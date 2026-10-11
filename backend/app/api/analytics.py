from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.session import get_db
from app.models.db_models import EvaluationSubmission, EvaluationResult, EvaluationHistory, BatchRecord
from app.schemas.evaluation_schemas import DashboardOverviewResponse, EvaluationListItem

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    verdict: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    batch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    evaluation_status: Optional[str] = Query(None),
    hallucination_presence: Optional[str] = Query(None),
):
    """Retrieve overview metrics for all evaluations or a filtered evaluation subset."""
    base_query = (
        db.query(EvaluationSubmission, EvaluationResult, EvaluationHistory)
        .join(EvaluationResult, EvaluationSubmission.id == EvaluationResult.evaluation_id)
        .join(EvaluationHistory, EvaluationSubmission.id == EvaluationHistory.evaluation_id)
    )

    if verdict:
        base_query = base_query.filter(EvaluationResult.verdict == verdict.strip().upper())
    if min_score is not None:
        base_query = base_query.filter(EvaluationResult.overall_score >= min_score)
    if max_score is not None:
        base_query = base_query.filter(EvaluationResult.overall_score <= max_score)
    if evaluation_status:
        base_query = base_query.filter(EvaluationSubmission.status == evaluation_status.strip().upper())
    if hallucination_presence:
        flag = hallucination_presence.strip().lower()
        if flag == "yes":
            base_query = base_query.filter(EvaluationHistory.hallucination_status.in_(["MEDIUM", "HIGH"]))
        elif flag == "no":
            base_query = base_query.filter(EvaluationHistory.hallucination_status == "LOW")
    if batch_id:
        eval_ids = (
            db.query(BatchRecord.evaluation_id)
            .filter(BatchRecord.batch_id == batch_id, BatchRecord.evaluation_id.is_not(None))
            .subquery()
        )
        base_query = base_query.filter(EvaluationSubmission.id.in_(eval_ids))
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            base_query = base_query.filter(EvaluationSubmission.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            base_query = base_query.filter(EvaluationSubmission.created_at < end_dt)
        except ValueError:
            pass

    total_evals = base_query.count()

    if total_evals == 0:
        return DashboardOverviewResponse(
            total_evaluations=0,
            average_overall_score=0.0,
            average_accuracy=0.0,
            average_relevance=0.0,
            average_completeness=0.0,
            average_hallucination_percentage=0.0,
            hallucination_frequency=0.0,
            pass_rate=0.0,
            needs_improvement_rate=0.0,
            fail_rate=0.0,
            score_trend=[],
            dimension_comparison={"Accuracy": 0.0, "Relevance": 0.0, "Completeness": 0.0, "HallucinationSafety": 0.0},
            verdict_distribution={"PASS": 0, "NEEDS_IMPROVEMENT": 0, "FAIL": 0},
            score_distribution={
                "overall": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
                "accuracy": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
                "relevance": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
                "completeness": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
                "hallucination": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
            },
            common_issues=[],
            recent_evaluations=[]
        )

    avg_overall = base_query.with_entities(func.avg(EvaluationResult.overall_score)).scalar() or 0.0
    avg_acc = base_query.with_entities(func.avg(EvaluationResult.accuracy_score)).scalar() or 0.0
    avg_rel = base_query.with_entities(func.avg(EvaluationResult.relevance_score)).scalar() or 0.0
    avg_comp = base_query.with_entities(func.avg(EvaluationResult.completeness_score)).scalar() or 0.0
    avg_hal = base_query.with_entities(func.avg(EvaluationResult.hallucination_score)).scalar() or 0.0

    pass_cnt = base_query.filter(EvaluationResult.verdict == "PASS").count()
    needs_cnt = base_query.filter(EvaluationResult.verdict == "NEEDS_IMPROVEMENT").count()
    fail_cnt = base_query.filter(EvaluationResult.verdict == "FAIL").count()

    pass_rate = round((pass_cnt / total_evals) * 100, 1)
    needs_rate = round((needs_cnt / total_evals) * 100, 1)
    fail_rate = round((fail_cnt / total_evals) * 100, 1)

    high_med_hal = base_query.filter(EvaluationHistory.hallucination_status.in_(["MEDIUM", "HIGH"])).count()
    halluc_freq = round((high_med_hal / total_evals) * 100, 1)

    recent_records = base_query.order_by(desc(EvaluationSubmission.created_at)).limit(8).all()
    recent_list = []
    for sub, res, hist in recent_records:
        recent_list.append(
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
                created_at=sub.created_at.strftime("%Y-%m-%d %H:%M")
            )
        )

    trend_query = (
        base_query.with_entities(EvaluationSubmission.created_at, EvaluationResult.overall_score)
        .order_by(EvaluationSubmission.created_at)
        .limit(15)
        .all()
    )
    score_trend = [
        {"date": created.strftime("%m/%d %H:%M"), "score": round(score, 1)}
        for created, score in trend_query
    ]

    # Calculate Score Distribution
    score_distribution = {
        "overall": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
        "accuracy": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
        "relevance": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
        "completeness": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
        "hallucination": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    }
    
    def get_bin(val):
        if val <= 20: return "0-20"
        if val <= 40: return "21-40"
        if val <= 60: return "41-60"
        if val <= 80: return "61-80"
        return "81-100"

    all_results = base_query.with_entities(
        EvaluationResult.overall_score,
        EvaluationResult.accuracy_score,
        EvaluationResult.relevance_score,
        EvaluationResult.completeness_score,
        EvaluationResult.hallucination_score,
        EvaluationResult.raw_metrics,
        EvaluationHistory.hallucination_status
    ).all()

    issues_count = {
        "Low Accuracy": 0,
        "Low Relevance": 0,
        "Incomplete Response": 0,
        "Hallucinated Claims": 0
    }
    hallucination_percentages = []

    for overall, acc, rel, comp, hal, raw_metrics, hal_status in all_results:
        verdict_metrics = (raw_metrics or {}).get("verdict", {})
        dimension_scores = verdict_metrics.get("dimension_scores", {})
        percentage = dimension_scores.get("hallucination_percentage")
        if percentage is not None:
            hallucination_percentages.append(float(percentage))
        if overall is not None: score_distribution["overall"][get_bin(overall)] += 1
        if acc is not None: 
            score_distribution["accuracy"][get_bin(acc * 20)] += 1
            if acc < 3.0: issues_count["Low Accuracy"] += 1
        if rel is not None: 
            score_distribution["relevance"][get_bin(rel * 20)] += 1
            if rel < 3.0: issues_count["Low Relevance"] += 1
        if comp is not None: 
            score_distribution["completeness"][get_bin(comp * 20)] += 1
            if comp < 3.0: issues_count["Incomplete Response"] += 1
        if hal is not None: score_distribution["hallucination"][get_bin(hal * 20)] += 1
        if hal_status in ["MEDIUM", "HIGH"]: issues_count["Hallucinated Claims"] += 1

    common_issues = [
        {"issue": k, "count": v} for k, v in sorted(issues_count.items(), key=lambda item: item[1], reverse=True) if v > 0
    ]

    return DashboardOverviewResponse(
        total_evaluations=total_evals,
        average_overall_score=round(avg_overall, 1),
        average_accuracy=round(avg_acc, 2),
        average_relevance=round(avg_rel, 2),
        average_completeness=round(avg_comp, 2),
        average_hallucination_percentage=round(
            sum(hallucination_percentages) / len(hallucination_percentages), 1
        ) if hallucination_percentages else 0.0,
        hallucination_frequency=halluc_freq,
        pass_rate=pass_rate,
        needs_improvement_rate=needs_rate,
        fail_rate=fail_rate,
        score_trend=score_trend,
        dimension_comparison={
            "Accuracy": round(avg_acc * 20, 1),
            "Relevance": round(avg_rel * 20, 1),
            "Completeness": round(avg_comp * 20, 1),
            "HallucinationSafety": round(avg_hal * 20, 1)
        },
        verdict_distribution={
            "PASS": pass_cnt,
            "NEEDS_IMPROVEMENT": needs_cnt,
            "FAIL": fail_cnt
        },
        score_distribution=score_distribution,
        common_issues=common_issues,
        recent_evaluations=recent_list
    )

@router.get("/insights")
def get_verification_insights(db: Session = Depends(get_db)):
    """Deep analytics on hallucination patterns, consistency, and dimension benchmarks."""
    overview = get_dashboard_overview(db)
    
    # Hallucination distribution
    low_cnt = db.query(EvaluationHistory).filter(EvaluationHistory.hallucination_status == "LOW").count()
    med_cnt = db.query(EvaluationHistory).filter(EvaluationHistory.hallucination_status == "MEDIUM").count()
    high_cnt = db.query(EvaluationHistory).filter(EvaluationHistory.hallucination_status == "HIGH").count()

    return {
        "overview": overview,
        "hallucination_distribution": {
            "Low Risk (Grounded)": low_cnt,
            "Medium Risk (Partial)": med_cnt,
            "High Risk (Contradicted/Fabricated)": high_cnt
        },
        "verdict_metrics": {
            "pass_rate": overview.pass_rate,
            "needs_improvement_rate": overview.needs_improvement_rate,
            "fail_rate": overview.fail_rate
        },
        "internship_benchmarks": {
            "target_pass_rate": 80.0,
            "target_hallucination_max": 15.0,
            "evaluation_engine_version": "AI Validation Engine v1.0.0"
        }
    }
