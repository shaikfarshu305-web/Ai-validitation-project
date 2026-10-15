from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# --- Input Request Schemas ---

class SingleEvaluationRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Submitted question or prompt")
    ai_response: str = Field(..., min_length=3, description="AI-generated response to verify")
    reference_answer: Optional[str] = Field(None, description="Ground truth or reference answer")
    source_information: Optional[str] = Field(None, description="User-provided source context / documents")

# --- Agent Output Schemas ---

class ClaimVerification(BaseModel):
    claim: str
    status: str = Field(..., description="SUPPORTED | UNSUPPORTED | CONTRADICTED")
    reasoning: str
    evidence: Optional[str] = None

class RelevanceOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=5.0, description="Relevance score (0 to 5)")
    reasoning: str
    strengths: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)

class AccuracyClaimAssessment(BaseModel):
    claim: str
    status: Literal["correct", "partially_correct", "incorrect", "unverifiable"]
    reasoning: str
    evidence: Optional[str] = None

class AccuracyOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=5.0, description="Accuracy score (0 to 5)")
    reasoning: str
    supporting_evidence: List[str] = Field(default_factory=list)
    incorrect_claims: List[str] = Field(default_factory=list)
    claim_assessments: List[AccuracyClaimAssessment] = Field(default_factory=list)
    factual_consistency: Optional[str] = None

class HallucinationOutput(BaseModel):
    hallucination_status: str = Field(..., description="LOW | MEDIUM | HIGH")
    hallucination_score: float = Field(..., ge=0.0, le=5.0, description="Safety score (5=clean/none, 0=extreme hallucination)")
    flagged_claims: List[ClaimVerification] = Field(default_factory=list)
    reasoning: str
    factual_consistency: Optional[str] = None

class CompletenessOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=5.0, description="Completeness score (0 to 5)")
    reasoning: str
    addressed_aspects: List[str] = Field(default_factory=list)
    missing_aspects: List[str] = Field(default_factory=list)

class VerdictOutput(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Aggregated weighted score (0-100)")
    verdict: str = Field(..., description="PASS | NEEDS_IMPROVEMENT | FAIL")
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    weights: Dict[str, float] = Field(default_factory=dict)
    major_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str

# --- RAG & Retrieval Schemas ---

class RetrievedChunk(BaseModel):
    chunk_id: str
    dataset: str
    title: str
    text: str
    similarity_score: float
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# --- Full Evaluation Response Schemas ---

class EvaluationDetailResponse(BaseModel):
    id: str
    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    source_information: Optional[str] = None
    created_at: str
    status: str
    
    # 4 Dimensions Summary
    relevance_score: float
    accuracy_score: float
    hallucination_score: float
    hallucination_percentage: float = Field(
        0.0, ge=0.0, le=100.0,
        description="Percentage of analyzed claims explicitly contradicted by available evidence.",
    )
    completeness_score: float
    overall_score: float
    verdict: str
    
    summary: Optional[str] = None
    major_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Deep dive agent payloads
    relevance_details: Optional[RelevanceOutput] = None
    accuracy_details: Optional[AccuracyOutput] = None
    hallucination_details: Optional[HallucinationOutput] = None
    completeness_details: Optional[CompletenessOutput] = None
    verdict_details: Optional[VerdictOutput] = None
    
    retrieved_evidence: List[RetrievedChunk] = Field(default_factory=list)

class EvaluationListItem(BaseModel):
    id: str
    question: str
    overall_score: float
    accuracy: float
    relevance: float
    hallucination: float
    completeness: float
    verdict: str
    hallucination_status: str
    created_at: str

# --- Batch Schemas ---

class BatchUploadResponse(BaseModel):
    batch_id: str
    filename: str
    total_records: int
    valid_records: int
    invalid_records: int
    sample_preview: List[Dict[str, Any]]

class BatchRecordItem(BaseModel):
    id: str
    row_index: int
    question: str
    ai_response: str
    reference_answer: Optional[str] = None
    source_information: Optional[str] = None
    overall_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    relevance_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    hallucination_percentage: Optional[float] = None
    completeness_score: Optional[float] = None
    verdict: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    evaluation_id: Optional[str] = None

class BatchStatusResponse(BaseModel):
    batch_id: str
    filename: str
    status: str
    total_records: int
    valid_records: int
    invalid_records: int
    processed_records: int
    average_overall_score: float
    average_accuracy: float
    average_relevance: float
    average_completeness: float
    average_hallucination_score: float
    average_hallucination_percentage: float
    hallucination_frequency: float
    pass_count: int
    needs_count: int
    fail_count: int
    records: List[BatchRecordItem] = Field(default_factory=list)

class BatchAnalyticsResponse(BaseModel):
    batch_id: str
    filename: str
    total_records: int
    successfully_evaluated: int
    failed_records: int
    average_overall_score: float
    average_accuracy: float
    average_relevance: float
    average_completeness: float
    hallucination_frequency: float
    verdict_distribution: Dict[str, int]
    dimension_averages: Dict[str, float]
    score_distribution: List[Dict[str, Any]]

# --- Knowledge Base Schemas ---

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: Optional[int] = 4
    dataset: Optional[str] = None

class KnowledgeSearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[RetrievedChunk]

class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_embeddings: int
    datasets: List[str]

class DataSourceInfo(BaseModel):
    name: str
    description: str
    num_records: int
    status: str
    last_indexed: str
    vector_index_status: str

# --- Analytics Schemas ---

class DashboardOverviewResponse(BaseModel):
    total_evaluations: int
    average_overall_score: float
    average_accuracy: float
    average_relevance: float
    average_completeness: float
    average_hallucination_percentage: float
    hallucination_frequency: float
    pass_rate: float
    needs_improvement_rate: float
    fail_rate: float
    score_trend: List[Dict[str, Any]]
    dimension_comparison: Dict[str, float]
    verdict_distribution: Dict[str, int]
    score_distribution: Dict[str, Dict[str, int]]
    common_issues: List[Dict[str, Any]]
    recent_evaluations: List[EvaluationListItem]

# --- Settings Schemas ---

class SettingsSchema(BaseModel):
    llm_provider: str = "local"
    model: str = "Local NLP & Semantic Analyzer"
    temperature: float = 0.2
    weight_accuracy: float = 0.30
    weight_hallucination: float = 0.25
    weight_relevance: float = 0.25
    weight_completeness: float = 0.20
    threshold_pass: float = 75.0
    threshold_needs_improvement: float = 50.0
    retrieval_top_k: int = 4
    chunk_size: int = 300
    chunk_overlap: int = 50
    hallucination_sensitivity: str = "standard"

class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    weight_accuracy: Optional[float] = None
    weight_hallucination: Optional[float] = None
    weight_relevance: Optional[float] = None
    weight_completeness: Optional[float] = None
    threshold_pass: Optional[float] = None
    threshold_needs_improvement: Optional[float] = None
    retrieval_top_k: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    hallucination_sensitivity: Optional[str] = None

# --- System Status Schemas ---

class ComponentStatus(BaseModel):
    name: str
    status: str  # ONLINE, WARNING, OFFLINE
    latency_ms: float
    details: str

class SystemStatusResponse(BaseModel):
    overall_status: str
    timestamp: str
    current_model: str
    indexed_chunks: int
    last_kb_update: str
    total_evaluations: int
    components: List[ComponentStatus]
