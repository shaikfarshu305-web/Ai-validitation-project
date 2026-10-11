import io
import csv
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import (
    BatchEvaluation,
    BatchRecord,
    EvaluationResult,
    SystemSettings,
)
from app.schemas.evaluation_schemas import (
    BatchUploadResponse,
    BatchStatusResponse,
    BatchRecordItem,
    BatchAnalyticsResponse,
    SingleEvaluationRequest
)
from app.orchestrator.evaluation_orchestrator import orchestrator
from app.config import migrate_legacy_default_weights

router = APIRouter(prefix="/batch", tags=["Batch Evaluation"])

SAMPLE_CSV_CONTENT = """question,ai_response,reference_answer,source_information
"Why is the sky blue?","The sky is blue due to Rayleigh scattering of sunlight by the atmospheric gases.","Rayleigh scattering causes shorter blue wavelengths to scatter more than red.","Atmospheric Optics"
"Can humans breathe underwater without equipment?","Yes, human lungs can extract oxygen directly from water if you breathe slowly.","Humans cannot breathe underwater without specialized scuba equipment; our lungs cannot extract dissolved oxygen.","Human Physiology"
"What causes solar eclipses?","A solar eclipse occurs when the Moon passes between Earth and the Sun, blocking sunlight.","The Moon casts a shadow on Earth when aligned with the Sun.","Astronomy Handbook"
"What is photosynthesis?","Photosynthesis is the process by which green plants convert light energy into chemical energy.","Plants use sunlight, water, and carbon dioxide to produce glucose and oxygen.","Plant Biology"
"At what temperature does water boil at sea level?","Water boils at about 45 degrees Celsius at standard sea-level pressure.","At standard atmospheric pressure, water boils at 100 degrees Celsius.","Basic Chemistry"
"What causes ocean tides?","Ocean tides are primarily caused by the gravitational pull of the Moon, with a smaller contribution from the Sun.","The Moon's gravity is the main cause of tides, while the Sun also contributes.","Oceanography"
"Why do Earth’s seasons change?","Seasons are caused by Earth's axial tilt as it orbits the Sun, which changes sunlight angle and day length.","Earth's tilted axis causes seasonal changes in solar angle and daylight duration.","Earth Science"
"Do antibiotics treat viral infections?","Antibiotics target bacteria and do not treat viruses such as influenza or the common cold.","Antibiotics work against bacterial infections, not viral infections.","Public Health"
"Can sound travel through a vacuum?","Sound cannot travel through a vacuum because it needs a material medium to carry vibrations.","Sound is a mechanical wave and requires a medium such as air, water, or a solid.","Physics"
"What causes the phases of the Moon?","The Moon's phases result from the changing portion of its sunlit half visible from Earth as it orbits Earth.","Moon phases occur as the visible fraction of the Moon's illuminated side changes during its orbit.","Astronomy"
"What is evaporation?","Evaporation is the change of a liquid into vapor at its surface, and it can occur below the boiling point.","Evaporation is the surface conversion of a liquid into gas.","Physical Science"
"What causes lightning?","Lightning is an electrical discharge caused by charge separation within a storm cloud or between a cloud and the ground.","Lightning is a sudden electrical discharge associated with charge buildup in thunderstorms.","Weather Science"
"""


def export_batch_pdf(batch_id: str, db: Session) -> bytes:
    """Generate a PDF summary and detail report for a batch from the actual stored records."""
    batch = db.query(BatchEvaluation).filter(BatchEvaluation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch evaluation not found.")

    records = db.query(BatchRecord).filter(BatchRecord.batch_id == batch_id).order_by(BatchRecord.row_index).all()
    evaluation_metrics = _batch_evaluation_metrics(records, db)
    hallucination_percentages = [
        metrics["hallucination_percentage"] for metrics in evaluation_metrics.values()
    ]
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#2A1B14"),
        spaceAfter=12,
        leading=22,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#5C3D2E"),
        spaceAfter=6,
        leading=16,
    )
    body_style = styles["BodyText"]
    body_style.leading = 14

    def safe(value):
        return value if value is not None else "N/A"

    summary_rows = [
        ["Metric", "Value"],
        ["Batch ID", batch.id],
        ["Filename", batch.filename],
        ["Status", batch.status],
        ["Total Records", str(batch.total_records)],
        ["Valid Records", str(batch.valid_records)],
        ["Invalid Records", str(batch.invalid_records)],
        ["Processed Records", str(batch.processed_records)],
        ["Average Overall Score", f"{batch.average_overall_score:.1f}"],
        ["Average Accuracy", f"{batch.average_accuracy:.2f}"],
        ["Average Relevance", f"{batch.average_relevance:.2f}"],
        ["Average Completeness", f"{batch.average_completeness:.2f}"],
        ["Average Hallucination Safety", f"{_average_metric(evaluation_metrics, 'hallucination_score'):.2f}/5"],
        ["Average Hallucination Percentage", f"{sum(hallucination_percentages) / len(hallucination_percentages):.1f}%" if hallucination_percentages else "N/A"],
        ["Hallucination Frequency", f"{batch.hallucination_frequency:.1f}%"],
        ["Pass Count", str(batch.pass_count)],
        ["Needs Improvement Count", str(batch.needs_count)],
        ["Fail Count", str(batch.fail_count)],
    ]

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []
    story.append(Paragraph("AI Response Validation System\nEvaluation Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Batch Summary", heading_style))
    summary_table = Table(summary_rows, colWidths=[220, 260])
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9D9C6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#D6C4AF")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Detailed Evaluation Results", heading_style))
    for rec in records:
        verdict_text = safe(rec.verdict)
        story.append(Paragraph(
            f"Row {rec.row_index}: {verdict_text} | Score {rec.overall_score if rec.overall_score is not None else 'N/A'}",
            styles["Heading3"],
        ))
        story.append(Paragraph(f"Question: {safe(rec.question)}", body_style))
        story.append(Paragraph(f"AI Response: {safe(rec.ai_response)}", body_style))
        story.append(Paragraph(f"Reference Answer: {safe(rec.reference_answer)}", body_style))
        story.append(Paragraph(f"Source Information: {safe(rec.source_information)}", body_style))
        detail_rows = [
            ["Dimension", "Value"],
            ["Relevance", str(rec.relevance_score) if rec.relevance_score is not None else "N/A"],
            ["Accuracy", str(rec.accuracy_score) if rec.accuracy_score is not None else "N/A"],
            ["Hallucination Safety", f"{rec.hallucination_score:.1f}/5" if rec.hallucination_score is not None else "N/A"],
            ["Hallucination Percentage", f"{evaluation_metrics.get(rec.evaluation_id, {}).get('hallucination_percentage', 0.0):.1f}%" if rec.evaluation_id else "N/A"],
            ["Completeness", str(rec.completeness_score) if rec.completeness_score is not None else "N/A"],
            ["Status", safe(rec.status)],
            ["Evaluation ID", safe(rec.evaluation_id)],
        ]
        detail_table = Table(detail_rows, colWidths=[200, 250])
        detail_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1E8D8")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#D6C4AF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ])
        )
        story.append(detail_table)
        story.append(Spacer(1, 12))

    doc.build(story)
    return buffer.getvalue()


def _batch_evaluation_metrics(records: List[BatchRecord], db: Session) -> dict:
    evaluation_ids = [record.evaluation_id for record in records if record.evaluation_id]
    if not evaluation_ids:
        return {}
    results = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_id.in_(evaluation_ids)
    ).all()
    return {
        result.evaluation_id: {
            "hallucination_score": result.hallucination_score,
            "hallucination_percentage": (
                (result.raw_metrics or {}).get("verdict", {})
                .get("dimension_scores", {}).get("hallucination_percentage", 0.0)
            ),
        }
        for result in results
    }


def _average_metric(metrics: dict, key: str) -> float:
    values = [item[key] for item in metrics.values() if item.get(key) is not None]
    return sum(values) / len(values) if values else 0.0


@router.get("/sample-csv")
def download_sample_csv():
    """Download a valid sample CSV file for batch evaluation."""
    return Response(
        content=SAMPLE_CSV_CONTENT,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ai_validation_sample_batch.csv"}
    )

@router.post("/upload", response_model=BatchUploadResponse)
async def upload_batch_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Validate uploaded CSV file:
    - Check columns: question, ai_response (required), reference_answer, source_information (optional)
    - Detect invalid/malformed rows
    - Count valid vs invalid rows
    - Pre-stage batch records in DB
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file encoding.")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file appears to be empty or missing headers.")

    field_map = {f.strip().lower(): f for f in reader.fieldnames}
    if "question" not in field_map or "ai_response" not in field_map:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns. CSV must contain 'question' and 'ai_response'. Found: {list(reader.fieldnames)}"
        )

    q_col = field_map["question"]
    r_col = field_map["ai_response"]
    ref_col = field_map.get("reference_answer")
    src_col = field_map.get("source_information")

    batch_id = str(uuid.uuid4())
    total_records = 0
    valid_records = 0
    invalid_records = 0
    sample_preview = []

    batch_eval = BatchEvaluation(
        id=batch_id,
        filename=file.filename,
        total_records=0,
        valid_records=0,
        invalid_records=0,
        processed_records=0,
        status="UPLOADED",
        created_at=datetime.utcnow()
    )
    db.add(batch_eval)

    for idx, row in enumerate(reader):
        total_records += 1
        q_val = (row.get(q_col) or "").strip()
        a_val = (row.get(r_col) or "").strip()
        ref_val = (row.get(ref_col) or "").strip() if ref_col else None
        src_val = (row.get(src_col) or "").strip() if src_col else None

        is_valid = True
        err_msg = None

        if not q_val:
            is_valid = False
            err_msg = "Empty question field"
        elif not a_val:
            is_valid = False
            err_msg = "Empty ai_response field"
        elif len(q_val) < 3 or len(a_val) < 3:
            is_valid = False
            err_msg = "Question or AI response too short (<3 chars)"

        if is_valid:
            valid_records += 1
            status_str = "VALID"
        else:
            invalid_records += 1
            status_str = "INVALID"

        rec = BatchRecord(
            id=str(uuid.uuid4()),
            batch_id=batch_id,
            row_index=idx + 1,
            question=q_val,
            ai_response=a_val,
            reference_answer=ref_val,
            source_information=src_val,
            status=status_str,
            error_message=err_msg,
            created_at=datetime.utcnow()
        )
        db.add(rec)

        if len(sample_preview) < 5:
            sample_preview.append({
                "row_index": idx + 1,
                "question": q_val[:80],
                "ai_response": a_val[:80],
                "status": status_str,
                "error": err_msg
            })

    batch_eval.total_records = total_records
    batch_eval.valid_records = valid_records
    batch_eval.invalid_records = invalid_records
    db.commit()

    return BatchUploadResponse(
        batch_id=batch_id,
        filename=file.filename,
        total_records=total_records,
        valid_records=valid_records,
        invalid_records=invalid_records,
        sample_preview=sample_preview
    )

@router.post("/{batch_id}/evaluate", response_model=BatchStatusResponse)
def run_batch_evaluation(batch_id: str, db: Session = Depends(get_db)):
    """
    Run multi-agent verification on all valid records in the batch.
    Does not halt on individual row errors.
    Calculates aggregated analytics.
    """
    batch = db.query(BatchEvaluation).filter(BatchEvaluation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch evaluation not found.")

    records = db.query(BatchRecord).filter(
        BatchRecord.batch_id == batch_id,
        BatchRecord.status == "VALID"
    ).all()

    # Load custom settings if available
    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    weights = None
    thresholds = None
    if sys_settings and sys_settings.settings_json:
        s = migrate_legacy_default_weights(sys_settings.settings_json)
        weights = {
            "accuracy": s.get("weight_accuracy", 0.35),
            "hallucination": s.get("weight_hallucination", 0.25),
            "relevance": s.get("weight_relevance", 0.25),
            "completeness": s.get("weight_completeness", 0.15)
        }
        thresholds = {
            "pass": s.get("threshold_pass", 75.0),
            "needs_improvement": s.get("threshold_needs_improvement", 50.0)
        }

    claim = db.execute(
        update(BatchEvaluation)
        .where(
            BatchEvaluation.id == batch_id,
            BatchEvaluation.status == "UPLOADED",
        )
        .values(status="PROCESSING")
    )
    db.commit()
    if claim.rowcount != 1:
        raise HTTPException(
            status_code=409,
            detail="This batch has already started or completed evaluation.",
        )
    db.refresh(batch)

    total_overall = 0.0
    total_acc = 0.0
    total_rel = 0.0
    total_hal = 0.0
    total_comp = 0.0
    evaluated_count = 0
    halluc_count = 0
    pass_cnt = 0
    needs_cnt = 0
    fail_cnt = 0

    for rec in records:
        try:
            req = SingleEvaluationRequest(
                question=rec.question,
                ai_response=rec.ai_response,
                reference_answer=rec.reference_answer,
                source_information=rec.source_information
            )
            eval_res = orchestrator.run_evaluation(db, req, custom_weights=weights, custom_thresholds=thresholds)

            rec.overall_score = eval_res["overall_score"]
            rec.accuracy_score = eval_res["accuracy_score"]
            rec.relevance_score = eval_res["relevance_score"]
            rec.hallucination_score = eval_res["hallucination_score"]
            rec.completeness_score = eval_res["completeness_score"]
            rec.verdict = eval_res["verdict"]
            rec.status = "EVALUATED"
            rec.evaluation_id = eval_res["id"]

            total_overall += eval_res["overall_score"]
            total_acc += eval_res["accuracy_score"]
            total_rel += eval_res["relevance_score"]
            total_hal += eval_res["hallucination_score"]
            total_comp += eval_res["completeness_score"]
            evaluated_count += 1

            if eval_res["verdict"] == "PASS":
                pass_cnt += 1
            elif eval_res["verdict"] == "NEEDS_IMPROVEMENT":
                needs_cnt += 1
            else:
                fail_cnt += 1

            if eval_res.get("hallucination_details", {}).get("hallucination_status") in ["MEDIUM", "HIGH"]:
                halluc_count += 1

        except Exception as e:
            db.rollback()
            failed_record = db.query(BatchRecord).filter(BatchRecord.id == rec.id).first()
            if failed_record:
                failed_record.status = "ERROR"
                failed_record.error_message = f"Evaluation error: {str(e)}"[:2000]
                db.commit()

        batch.processed_records = evaluated_count
        db.commit()

    if evaluated_count > 0:
        batch.average_overall_score = round(total_overall / evaluated_count, 1)
        batch.average_accuracy = round(total_acc / evaluated_count, 2)
        batch.average_relevance = round(total_rel / evaluated_count, 2)
        batch.average_completeness = round(total_comp / evaluated_count, 2)
        batch.hallucination_frequency = round((halluc_count / evaluated_count) * 100, 1)
        batch.pass_count = pass_cnt
        batch.needs_count = needs_cnt
        batch.fail_count = fail_cnt

    batch.status = "COMPLETED"
    db.commit()

    return get_batch_status(batch_id, db)

@router.get("/{batch_id}", response_model=BatchStatusResponse)
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Retrieve full batch status and individual record items."""
    batch = db.query(BatchEvaluation).filter(BatchEvaluation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch evaluation not found.")

    records = db.query(BatchRecord).filter(BatchRecord.batch_id == batch_id).order_by(BatchRecord.row_index).all()
    evaluation_metrics = _batch_evaluation_metrics(records, db)

    items = []
    for r in records:
        items.append(BatchRecordItem(
            id=r.id,
            row_index=r.row_index,
            question=r.question,
            ai_response=r.ai_response,
            reference_answer=r.reference_answer,
            source_information=r.source_information,
            overall_score=r.overall_score,
            accuracy_score=r.accuracy_score,
            relevance_score=r.relevance_score,
            hallucination_score=r.hallucination_score,
            hallucination_percentage=evaluation_metrics.get(r.evaluation_id, {}).get("hallucination_percentage"),
            completeness_score=r.completeness_score,
            verdict=r.verdict,
            status=r.status,
            error_message=r.error_message,
            evaluation_id=r.evaluation_id
        ))

    return BatchStatusResponse(
        batch_id=batch.id,
        filename=batch.filename,
        status=batch.status,
        total_records=batch.total_records,
        valid_records=batch.valid_records,
        invalid_records=batch.invalid_records,
        processed_records=batch.processed_records,
        average_overall_score=batch.average_overall_score,
        average_accuracy=batch.average_accuracy,
        average_relevance=batch.average_relevance,
        average_completeness=batch.average_completeness,
        average_hallucination_score=round(_average_metric(evaluation_metrics, "hallucination_score"), 2),
        average_hallucination_percentage=round(_average_metric(evaluation_metrics, "hallucination_percentage"), 1),
        hallucination_frequency=batch.hallucination_frequency,
        pass_count=batch.pass_count,
        needs_count=batch.needs_count,
        fail_count=batch.fail_count,
        records=items
    )

@router.get("/{batch_id}/analytics", response_model=BatchAnalyticsResponse)
def get_batch_analytics(batch_id: str, db: Session = Depends(get_db)):
    """Detailed analytics, score histograms, and verdict distributions for batch."""
    batch = db.query(BatchEvaluation).filter(BatchEvaluation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch evaluation not found.")

    records = db.query(BatchRecord).filter(
        BatchRecord.batch_id == batch_id,
        BatchRecord.status == "EVALUATED"
    ).all()

    # Score buckets
    buckets = {"90-100": 0, "75-89": 0, "50-74": 0, "0-49": 0}
    for r in records:
        if r.overall_score is not None:
            s = r.overall_score
            if s >= 90:
                buckets["90-100"] += 1
            elif s >= 75:
                buckets["75-89"] += 1
            elif s >= 50:
                buckets["50-74"] += 1
            else:
                buckets["0-49"] += 1

    score_dist = [{"range": k, "count": v} for k, v in buckets.items()]

    return BatchAnalyticsResponse(
        batch_id=batch.id,
        filename=batch.filename,
        total_records=batch.total_records,
        successfully_evaluated=batch.processed_records,
        failed_records=batch.invalid_records,
        average_overall_score=batch.average_overall_score,
        average_accuracy=batch.average_accuracy,
        average_relevance=batch.average_relevance,
        average_completeness=batch.average_completeness,
        hallucination_frequency=batch.hallucination_frequency,
        verdict_distribution={
            "PASS": batch.pass_count,
            "NEEDS_IMPROVEMENT": batch.needs_count,
            "FAIL": batch.fail_count
        },
        dimension_averages={
            "Accuracy": batch.average_accuracy,
            "Relevance": batch.average_relevance,
            "Completeness": batch.average_completeness,
            "HallucinationSafety": round(
                _average_metric(_batch_evaluation_metrics(records, db), "hallucination_score"), 2
            ),
            "HallucinationPercentage": round(
                _average_metric(_batch_evaluation_metrics(records, db), "hallucination_percentage"), 1
            ),
        },
        score_distribution=score_dist
    )

@router.get("/{batch_id}/export")
def export_batch_results(batch_id: str, db: Session = Depends(get_db)):
    """Export evaluated batch records to CSV format."""
    batch = db.query(BatchEvaluation).filter(BatchEvaluation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch evaluation not found.")

    records = db.query(BatchRecord).filter(BatchRecord.batch_id == batch_id).order_by(BatchRecord.row_index).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Row", "Question", "AI Response", "Reference Answer",
        "Overall Score", "Verdict", "Accuracy (0-5)", "Relevance (0-5)",
        "Hallucination Safety (0-5)", "Hallucination Percentage (verified contradicted claims)",
        "Completeness (0-5)", "Status", "Evaluation ID"
    ])
    evaluation_metrics = _batch_evaluation_metrics(records, db)

    for r in records:
        writer.writerow([
            r.row_index,
            r.question,
            r.ai_response,
            r.reference_answer or "",
            r.overall_score or "",
            r.verdict or "",
            r.accuracy_score or "",
            r.relevance_score or "",
            r.hallucination_score or "",
            evaluation_metrics.get(r.evaluation_id, {}).get("hallucination_percentage", 0.0),
            r.completeness_score or "",
            r.status,
            r.evaluation_id or ""
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evaluated_{batch.filename}"}
    )


@router.get("/{batch_id}/export-pdf")
def export_batch_pdf_route(batch_id: str, db: Session = Depends(get_db)):
    """Export a professional PDF report for the batch using the stored evaluation results."""
    pdf_bytes = export_batch_pdf(batch_id, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ai_validation_batch_report_{batch_id}.pdf"},
    )
