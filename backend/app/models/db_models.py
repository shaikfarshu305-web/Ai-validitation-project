import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class EvaluationSubmission(Base):
    __tablename__ = "evaluation_submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    question = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=True)
    source_information = Column(Text, nullable=True)
    status = Column(String(50), default="COMPLETED")  # PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    result = relationship("EvaluationResult", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    agent_evaluations = relationship("AgentEvaluation", back_populates="submission", cascade="all, delete-orphan")
    history_entry = relationship("EvaluationHistory", back_populates="submission", uselist=False, cascade="all, delete-orphan")

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(String(36), ForeignKey("evaluation_submissions.id"), nullable=False, unique=True)
    
    # 4 Core Dimension Scores (0-5 scale)
    relevance_score = Column(Float, nullable=False, default=0.0)
    accuracy_score = Column(Float, nullable=False, default=0.0)
    hallucination_score = Column(Float, nullable=False, default=0.0)  # Safety score 0-5 (5 = clean/no hallucination)
    completeness_score = Column(Float, nullable=False, default=0.0)
    
    # Aggregated Weighted Score (0-100) & Verdict
    overall_score = Column(Float, nullable=False, default=0.0)
    verdict = Column(String(50), nullable=False, default="NEEDS_IMPROVEMENT")  # PASS, NEEDS_IMPROVEMENT, FAIL
    
    # Qualitative Insights
    summary = Column(Text, nullable=True)
    major_issues = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    raw_metrics = Column(JSON, default=dict)
    retrieved_evidence = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("EvaluationSubmission", back_populates="result")

class AgentEvaluation(Base):
    __tablename__ = "agent_evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(String(36), ForeignKey("evaluation_submissions.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)  # RelevanceJudge, AccuracyJudge, HallucinationDetector, CompletenessJudge, VerdictAgent
    score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    evidence = Column(JSON, default=list)
    metadata_info = Column(JSON, default=dict)
    execution_time_ms = Column(Float, default=0.0)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("EvaluationSubmission", back_populates="agent_evaluations")

class BatchEvaluation(Base):
    __tablename__ = "batch_evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    
    # Batch Analytics Averages
    average_overall_score = Column(Float, default=0.0)
    average_accuracy = Column(Float, default=0.0)
    average_relevance = Column(Float, default=0.0)
    average_completeness = Column(Float, default=0.0)
    hallucination_frequency = Column(Float, default=0.0)
    pass_count = Column(Integer, default=0)
    needs_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    
    status = Column(String(50), default="COMPLETED")  # UPLOADED, PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    records = relationship("BatchRecord", back_populates="batch", cascade="all, delete-orphan")

class BatchRecord(Base):
    __tablename__ = "batch_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), ForeignKey("batch_evaluations.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=True)
    source_information = Column(Text, nullable=True)
    
    overall_score = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    hallucination_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    verdict = Column(String(50), nullable=True)
    
    status = Column(String(50), default="VALID")  # VALID, INVALID, EVALUATED, ERROR
    error_message = Column(Text, nullable=True)
    evaluation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("BatchEvaluation", back_populates="records")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset = Column(String(100), nullable=False)  # TruthfulQA, SQuAD, Custom
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    num_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id"), nullable=False)
    dataset = Column(String(100), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    vector_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")

class DatasetSource(Base):
    __tablename__ = "dataset_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)  # TruthfulQA, SQuAD
    description = Column(Text, nullable=True)
    num_records = Column(Integer, default=0)
    status = Column(String(50), default="INDEXED")
    last_indexed = Column(DateTime, default=datetime.utcnow)
    vector_index_status = Column(String(50), default="READY")

class EvaluationHistory(Base):
    __tablename__ = "evaluation_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(String(36), ForeignKey("evaluation_submissions.id"), nullable=False)
    question_preview = Column(String(255), nullable=False)
    overall_score = Column(Float, nullable=False)
    verdict = Column(String(50), nullable=False)
    hallucination_status = Column(String(50), default="LOW")
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("EvaluationSubmission", back_populates="history_entry")

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    settings_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
