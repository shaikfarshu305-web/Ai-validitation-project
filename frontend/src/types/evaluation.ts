export interface ClaimVerification {
  claim: string;
  status: 'supported' | 'unsupported' | 'contradicted';
  reasoning: string;
  evidence?: string;
}

export interface RelevanceOutput {
  score: number;
  reasoning: string;
  strengths: string[];
  issues: string[];
}

export interface AccuracyOutput {
  score: number;
  reasoning: string;
  supporting_evidence: string[];
  incorrect_claims: string[];
  claim_assessments: Array<{
    claim: string;
    status: 'correct' | 'partially_correct' | 'incorrect' | 'unverifiable';
    reasoning: string;
    evidence?: string;
  }>;
  factual_consistency?: 'CONSISTENT' | 'PARTIALLY_CONSISTENT' | 'CONTRADICTORY' | 'UNSUPPORTED';
}

export interface HallucinationOutput {
  hallucination_status: 'LOW' | 'MEDIUM' | 'HIGH';
  hallucination_score: number;
  flagged_claims: ClaimVerification[];
  reasoning: string;
  factual_consistency?: 'CONSISTENT' | 'PARTIALLY_CONSISTENT' | 'CONTRADICTORY' | 'UNSUPPORTED';
}

export interface CompletenessOutput {
  score: number;
  reasoning: string;
  addressed_aspects: string[];
  missing_aspects: string[];
}

export interface VerdictOutput {
  overall_score: number;
  verdict: 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL';
  dimension_scores: {
    accuracy?: number;
    hallucination_safety?: number;
    relevance?: number;
    completeness?: number;
  };
  weights?: {
    accuracy?: number;
    hallucination_safety?: number;
    relevance?: number;
    completeness?: number;
  };
  major_issues: string[];
  recommendations: string[];
  summary: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  dataset: string;
  title: string;
  text: string;
  similarity_score: number;
  source?: string;
  metadata?: Record<string, any>;
}

export interface EvaluationDetail {
  id: string;
  question: string;
  ai_response: string;
  reference_answer?: string;
  source_information?: string;
  created_at: string;
  status: string;
  relevance_score: number;
  accuracy_score: number;
  hallucination_score: number;
  hallucination_percentage: number;
  completeness_score: number;
  overall_score: number;
  verdict: 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL';
  summary?: string;
  major_issues: string[];
  recommendations: string[];
  relevance_details?: RelevanceOutput;
  accuracy_details?: AccuracyOutput;
  hallucination_details?: HallucinationOutput;
  completeness_details?: CompletenessOutput;
  verdict_details?: VerdictOutput;
  retrieved_evidence: RetrievedChunk[];
}

export interface EvaluationListItem {
  id: string;
  question: string;
  overall_score: number;
  accuracy: number;
  relevance: number;
  hallucination: number;
  completeness: number;
  verdict: 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL';
  hallucination_status: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at: string;
}

export interface DashboardFilters {
  verdict?: string;
  min_score?: number;
  max_score?: number;
  batch_id?: string;
  start_date?: string;
  end_date?: string;
  evaluation_status?: string;
  hallucination_presence?: string;
}

export interface DashboardOverview {
  total_evaluations: number;
  average_overall_score: number;
  average_accuracy: number;
  average_relevance: number;
  average_completeness: number;
  average_hallucination_percentage: number;
  hallucination_frequency: number;
  pass_rate: number;
  needs_improvement_rate: number;
  fail_rate: number;
  score_trend: Array<{ date: string; score: number }>;
  dimension_comparison: {
    Accuracy: number;
    Relevance: number;
    Completeness: number;
    HallucinationSafety: number;
  };
  verdict_distribution: {
    PASS: number;
    NEEDS_IMPROVEMENT: number;
    FAIL: number;
  };
  score_distribution: Record<string, Record<string, number>>;
  common_issues: Array<{ issue: string; count: number }>;
  recent_evaluations: EvaluationListItem[];
}

export interface BatchRecordItem {
  id: string;
  row_index: number;
  question: string;
  ai_response: string;
  reference_answer?: string;
  source_information?: string;
  overall_score?: number;
  accuracy_score?: number;
  relevance_score?: number;
  hallucination_score?: number;
  hallucination_percentage?: number;
  completeness_score?: number;
  verdict?: 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL';
  status: 'VALID' | 'INVALID' | 'EVALUATED' | 'ERROR';
  error_message?: string;
  evaluation_id?: string;
}

export interface BatchStatus {
  batch_id: string;
  filename: string;
  status: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  processed_records: number;
  average_overall_score: number;
  average_accuracy: number;
  average_relevance: number;
  average_completeness: number;
  average_hallucination_score: number;
  average_hallucination_percentage: number;
  hallucination_frequency: number;
  pass_count: number;
  needs_count: number;
  fail_count: number;
  records: BatchRecordItem[];
}

export interface ComponentStatus {
  name: string;
  status: 'ONLINE' | 'WARNING' | 'OFFLINE';
  latency_ms: number;
  details: string;
}

export interface SystemStatusData {
  overall_status: string;
  timestamp: string;
  current_model: string;
  indexed_chunks: number;
  last_kb_update: string;
  total_evaluations: number;
  components: ComponentStatus[];
}

export interface DataSourceItem {
  name: string;
  description: string;
  num_records: number;
  status: string;
  last_indexed: string;
  vector_index_status: string;
}

export interface SystemSettingsConfig {
  llm_provider: string;
  model: string;
  temperature: number;
  weight_accuracy: number;
  weight_hallucination: number;
  weight_relevance: number;
  weight_completeness: number;
  threshold_pass: number;
  threshold_needs_improvement: number;
  retrieval_top_k: number;
  chunk_size: number;
  chunk_overlap: number;
  hallucination_sensitivity: string;
}
