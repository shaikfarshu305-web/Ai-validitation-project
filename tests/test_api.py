import pytest
import csv
import io
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base, SessionLocal, init_db
from app.api.evaluate import evaluate_response, list_evaluations, get_evaluation_detail
from app.api.system import get_system_status
from app.api.knowledge import get_knowledge_stats, test_retrieval_query as kb_search_endpoint
from app.api.batch import download_sample_csv, export_batch_pdf, run_batch_evaluation
from app.models.db_models import BatchEvaluation, BatchRecord
from app.schemas.evaluation_schemas import SingleEvaluationRequest, KnowledgeSearchRequest

def test_system_status_endpoint():
    init_db()
    db = SessionLocal()
    try:
        res = get_system_status(db)
        assert res.overall_status == "ONLINE"
        assert len(res.components) >= 5
    finally:
        db.close()

def test_knowledge_base_stats():
    db = SessionLocal()
    try:
        res = get_knowledge_stats(db)
        assert res.total_chunks >= 0
        assert len(res.datasets) >= 1
    finally:
        db.close()

def test_kb_search_feature():
    req = KnowledgeSearchRequest(query="Earth axial tilt seasons", top_k=2)
    res = kb_search_endpoint(req)
    assert res.query == "Earth axial tilt seasons"
    assert len(res.results) >= 0


def test_sample_batch_csv_contains_real_inputs_only():
    response = download_sample_csv()
    records = list(csv.DictReader(io.StringIO(response.body.decode("utf-8"))))

    assert len(records) == 12
    assert all(record["question"].strip() for record in records)
    assert all(record["ai_response"].strip() for record in records)
    assert all(record["reference_answer"].strip() for record in records)

def test_single_evaluation_flow():
    db = SessionLocal()
    try:
        req = SingleEvaluationRequest(
            question="What causes the Northern Lights?",
            ai_response="The Northern Lights (aurora borealis) are caused by collisions between electrically charged particles released from the Sun and gases in Earth's atmosphere.",
            reference_answer="Solar wind particles collide with nitrogen and oxygen atoms in Earth's upper atmosphere.",
            source_information="Geophysics Reference"
        )
        res = evaluate_response(req, db)
        assert res["id"] is not None
        assert res["overall_score"] >= 60.0
        assert res["verdict"] in ["PASS", "NEEDS_IMPROVEMENT"]
        assert res["relevance_score"] >= 3.0
        assert res["accuracy_score"] >= 3.0
        assert res["hallucination_score"] >= 3.0

        # Test listing
        eval_list = list_evaluations(db=db)
        assert len(eval_list) >= 1

        # Test getting detail
        detail = get_evaluation_detail(res["id"], db)
        assert detail.id == res["id"]
        assert detail.overall_score == res["overall_score"]
    finally:
        db.close()


def test_batch_pdf_export():
    db = SessionLocal()
    try:
        batch = db.query(__import__('app.models.db_models', fromlist=['BatchEvaluation']).BatchEvaluation).first()
        if batch is None:
            batch = __import__('app.models.db_models', fromlist=['BatchEvaluation']).BatchEvaluation(
                id='test-batch-pdf-export',
                filename='demo.csv',
                total_records=1,
                valid_records=1,
                invalid_records=0,
                processed_records=1,
                average_overall_score=82.5,
                average_accuracy=4.1,
                average_relevance=4.4,
                average_completeness=4.0,
                hallucination_frequency=10.0,
                pass_count=1,
                needs_count=0,
                fail_count=0,
                status='COMPLETED'
            )
            db.add(batch)
            db.flush()

            record = __import__('app.models.db_models', fromlist=['BatchRecord']).BatchRecord(
                id='test-batch-pdf-record',
                batch_id=batch.id,
                row_index=1,
                question='What happens during a solar eclipse?',
                ai_response='The Moon passes between Earth and the Sun, briefly casting a shadow on Earth.',
                reference_answer='A solar eclipse occurs when the Moon moves between Earth and the Sun and blocks part of sunlight.',
                source_information='Astronomy',
                overall_score=82.5,
                accuracy_score=4.5,
                relevance_score=4.6,
                hallucination_score=4.8,
                completeness_score=4.2,
                verdict='PASS',
                status='EVALUATED',
                evaluation_id='sample-eval-1'
            )
            db.add(record)
            db.commit()

        pdf_bytes = export_batch_pdf(batch.id, db)
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert pdf_bytes.startswith(b'%PDF')
    finally:
        db.close()


def test_batch_evaluation_uses_orchestrator_once(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine)()
    calls = []

    def evaluate(db, req, custom_weights=None, custom_thresholds=None):
        calls.append(req)
        if len(calls) == 1:
            raise RuntimeError("row evaluation failed")
        return {
            "id": "real-evaluation-id",
            "overall_score": 81.0,
            "accuracy_score": 4.0,
            "relevance_score": 4.5,
            "hallucination_score": 4.0,
            "completeness_score": 4.0,
            "verdict": "PASS",
            "hallucination_details": {"hallucination_status": "LOW"},
        }

    monkeypatch.setattr("app.api.batch.orchestrator.run_evaluation", evaluate)
    batch = BatchEvaluation(
        id="batch-once",
        filename="responses.csv",
        total_records=2,
        valid_records=2,
        invalid_records=0,
        status="UPLOADED",
    )
    test_session.add(batch)
    test_session.add(BatchRecord(
        id="record-once",
        batch_id=batch.id,
        row_index=1,
        question="What is photosynthesis?",
        ai_response="Plants convert light energy into chemical energy.",
        status="VALID",
    ))
    test_session.add(BatchRecord(
        id="record-after-error",
        batch_id=batch.id,
        row_index=2,
        question="What is evaporation?",
        ai_response="Liquid water changes into water vapor.",
        status="VALID",
    ))
    test_session.commit()

    try:
        result = run_batch_evaluation("batch-once", test_session)
        assert result.processed_records == 1
        assert result.records[0].status == "ERROR"
        assert result.records[1].evaluation_id == "real-evaluation-id"
        assert len(calls) == 2

        with pytest.raises(HTTPException) as exc_info:
            run_batch_evaluation("batch-once", test_session)
        assert exc_info.value.status_code == 409
        assert len(calls) == 2
    finally:
        test_session.close()
        engine.dispose()


def test_batch_evaluates_repeated_question_and_response_with_its_own_reference(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine)()

    calls = []

    def evaluate(db, req, custom_weights=None, custom_thresholds=None):
        calls.append(req)
        return {
            "id": f"evaluation-{len(calls)}",
            "overall_score": 80.0,
            "accuracy_score": 4.0,
            "relevance_score": 4.0,
            "hallucination_score": 4.0,
            "completeness_score": 4.0,
            "verdict": "PASS",
            "hallucination_details": {"hallucination_status": "LOW"},
        }

    monkeypatch.setattr("app.api.batch.orchestrator.run_evaluation", evaluate)
    batch = BatchEvaluation(
        id="duplicate-batch",
        filename="responses.csv",
        total_records=2,
        valid_records=2,
        invalid_records=0,
        status="UPLOADED",
    )
    test_session.add(batch)
    test_session.add(BatchRecord(
        id="duplicate-record-a",
        batch_id=batch.id,
        row_index=1,
        question="What is gravity?",
        ai_response="Gravity attracts objects with mass.",
        reference_answer="Reference answer A",
        status="VALID",
    ))
    test_session.add(BatchRecord(
        id="duplicate-record-b",
        batch_id=batch.id,
        row_index=2,
        question="What is gravity?",
        ai_response="Gravity attracts objects with mass.",
        reference_answer="Reference answer B",
        status="VALID",
    ))
    test_session.commit()

    try:
        result = run_batch_evaluation("duplicate-batch", test_session)
        assert result.processed_records == 2
        assert result.records[0].status == "EVALUATED"
        assert result.records[1].status == "EVALUATED"
        assert [call.reference_answer for call in calls] == ["Reference answer A", "Reference answer B"]
    finally:
        test_session.close()
        engine.dispose()
