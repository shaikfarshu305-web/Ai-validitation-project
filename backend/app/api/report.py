from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.database.session import get_db
from app.models.db_models import EvaluationSubmission, EvaluationResult, EvaluationHistory, BatchRecord

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/pdf")
def generate_pdf_report(
    db: Session = Depends(get_db),
    evaluation_id: str = Query(None, description="Generate report for a single evaluation"),
    batch_id: str = Query(None, description="Generate report for an entire batch")
):
    if not evaluation_id and not batch_id:
        raise HTTPException(status_code=400, detail="Must provide evaluation_id or batch_id")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements.append(Paragraph("AI Response Validation System", title_style))
    elements.append(Paragraph("Evaluation Report", styles['Heading1']))
    elements.append(Spacer(1, 12))

    if evaluation_id:
        # Single evaluation report
        submission = db.query(EvaluationSubmission).filter(EvaluationSubmission.id == evaluation_id).first()
        result = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation_id).first()
        
        if not submission or not result:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        verdict_metrics = (result.raw_metrics or {}).get("verdict", {})
        hallucination_percentage = verdict_metrics.get("dimension_scores", {}).get(
            "hallucination_percentage", 0.0
        )
        
        elements.append(Paragraph(f"Evaluation ID: {evaluation_id}", normal_style))
        elements.append(Paragraph(f"Date: {submission.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Summary Table
        data = [
            ["Dimension", "Score"],
            ["Overall Score", f"{result.overall_score:.1f}/100"],
            ["Accuracy", f"{result.accuracy_score:.1f}/5"],
            ["Relevance", f"{result.relevance_score:.1f}/5"],
            ["Completeness", f"{result.completeness_score:.1f}/5"],
            ["Hallucination Safety", f"{result.hallucination_score * 2:.1f}/10"],
            ["Hallucination Percentage (verified contradicted claims)", f"{hallucination_percentage:.1f}%"],
            ["Verdict", result.verdict]
        ]
        
        t = Table(data, colWidths=[200, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 24))
        
        # QA Details
        elements.append(Paragraph("Question:", heading_style))
        elements.append(Paragraph(submission.question, normal_style))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("AI Response:", heading_style))
        elements.append(Paragraph(submission.ai_response, normal_style))
        elements.append(Spacer(1, 12))
        
        if submission.reference_answer:
            elements.append(Paragraph("Reference Answer:", heading_style))
            elements.append(Paragraph(submission.reference_answer, normal_style))
            elements.append(Spacer(1, 12))
            
        elements.append(Paragraph("Summary / Reasoning:", heading_style))
        elements.append(Paragraph(result.summary or "No summary provided.", normal_style))
        elements.append(Spacer(1, 12))
        
        if result.major_issues:
            elements.append(Paragraph("Major Issues (Flagged):", heading_style))
            for issue in result.major_issues:
                elements.append(Paragraph(f"• {issue}", normal_style))
            elements.append(Spacer(1, 12))
            
        if result.recommendations:
            elements.append(Paragraph("Recommendations:", heading_style))
            for rec in result.recommendations:
                elements.append(Paragraph(f"• {rec}", normal_style))
            elements.append(Spacer(1, 12))
            
        if result.retrieved_evidence:
            elements.append(Paragraph("Retrieved Evidence:", heading_style))
            for ev in result.retrieved_evidence:
                title = ev.get('title', 'Unknown Source') if isinstance(ev, dict) else getattr(ev, 'title', 'Unknown Source')
                elements.append(Paragraph(f"Source: {title}", styles['Heading3']))
                elements.append(Spacer(1, 6))
        
    elif batch_id:
        # Batch report
        records = db.query(BatchRecord).filter(BatchRecord.batch_id == batch_id).all()
        if not records:
            raise HTTPException(status_code=404, detail="Batch not found or empty")
            
        elements.append(Paragraph(f"Batch ID: {batch_id}", normal_style))
        elements.append(Paragraph(f"Total Records: {len(records)}", normal_style))
        elements.append(Spacer(1, 12))
        
        # We can add more comprehensive logic for batch, like looping over records and printing summaries.
        # But this suffices for now to satisfy PDF generation from real data.
        
        data = [["Row", "Status", "Score", "Verdict"]]
        for r in records:
            data.append([str(r.row_index), r.status, f"{r.overall_score:.1f}" if r.overall_score else "N/A", r.verdict or "N/A"])
            
        t = Table(data, colWidths=[50, 100, 75, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=Evaluation_Report.pdf"}
    )
