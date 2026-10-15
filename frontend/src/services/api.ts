import {
  EvaluationDetail,
  EvaluationListItem,
  DashboardOverview,
  DashboardFilters,
  BatchStatus,
  SystemStatusData,
  DataSourceItem,
  SystemSettingsConfig,
  RetrievedChunk
} from '../types/evaluation';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV
    ? 'http://localhost:8000/api'
    : 'https://ai-validation-project-1.onrender.com/api')
).replace(/\/+$/, '');

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMessage = `HTTP Error ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) errMessage = err.detail;
    } catch {
      // fallback
    }
    throw new Error(errMessage);
  }
  return res.json();
}

export const api = {
  // --- Analytics & Dashboard ---
  getDashboardOverview: async (filters?: DashboardFilters): Promise<DashboardOverview> => {
    const query = new URLSearchParams();
    if (filters?.verdict) query.append('verdict', filters.verdict);
    if (filters?.min_score !== undefined) query.append('min_score', String(filters.min_score));
    if (filters?.max_score !== undefined) query.append('max_score', String(filters.max_score));
    if (filters?.batch_id) query.append('batch_id', filters.batch_id);
    if (filters?.start_date) query.append('start_date', filters.start_date);
    if (filters?.end_date) query.append('end_date', filters.end_date);
    if (filters?.evaluation_status) query.append('evaluation_status', filters.evaluation_status);
    if (filters?.hallucination_presence) query.append('hallucination_presence', filters.hallucination_presence);

    const res = await fetch(`${API_BASE}/analytics/overview${query.toString() ? `?${query.toString()}` : ''}`);
    return handleResponse<DashboardOverview>(res);
  },

  getVerificationInsights: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/analytics/insights`);
    return handleResponse<any>(res);
  },

  // --- Evaluations ---
  evaluateResponse: async (payload: {
    question: string;
    ai_response: string;
    reference_answer?: string;
    source_information?: string;
  }): Promise<EvaluationDetail> => {
    const res = await fetch(`${API_BASE}/evaluations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<EvaluationDetail>(res);
  },

  listEvaluations: async (params?: {
    search?: string;
    verdict?: string;
    min_score?: number;
    max_score?: number;
    hallucination_status?: string;
  }): Promise<EvaluationListItem[]> => {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.verdict) query.append('verdict', params.verdict);
    if (params?.min_score !== undefined) query.append('min_score', params.min_score.toString());
    if (params?.max_score !== undefined) query.append('max_score', params.max_score.toString());
    if (params?.hallucination_status) query.append('hallucination_status', params.hallucination_status);

    const res = await fetch(`${API_BASE}/evaluations?${query.toString()}`);
    return handleResponse<EvaluationListItem[]>(res);
  },

  getEvaluationDetail: async (id: string): Promise<EvaluationDetail> => {
    const res = await fetch(`${API_BASE}/evaluations/${id}`);
    return handleResponse<EvaluationDetail>(res);
  },

  deleteEvaluation: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/evaluations/${id}`, { method: 'DELETE' });
    return handleResponse<void>(res);
  },

  // --- Batch Evaluation ---
  uploadBatchCSV: async (file: File): Promise<{
    batch_id: string;
    filename: string;
    total_records: number;
    valid_records: number;
    invalid_records: number;
    sample_preview: any[];
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/batch/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<any>(res);
  },

  runBatchEvaluation: async (batchId: string): Promise<BatchStatus> => {
    const res = await fetch(`${API_BASE}/batch/${batchId}/evaluate`, {
      method: 'POST',
    });
    return handleResponse<BatchStatus>(res);
  },

  getBatchStatus: async (batchId: string): Promise<BatchStatus> => {
    const res = await fetch(`${API_BASE}/batch/${batchId}`);
    return handleResponse<BatchStatus>(res);
  },

  getBatchAnalytics: async (batchId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/batch/${batchId}/analytics`);
    return handleResponse<any>(res);
  },

  getSampleCSVUrl: (): string => `${API_BASE}/batch/sample-csv`,
  getExportBatchUrl: (batchId: string): string => `${API_BASE}/batch/${batchId}/export`,
  getBatchPdfUrl: (batchId: string): string => `${API_BASE}/reports/pdf?batch_id=${batchId}`,
  getExportEvaluationPdfUrl: (evalId: string): string => `${API_BASE}/reports/pdf?evaluation_id=${evalId}`,

  // --- Knowledge Base & RAG ---
  getKnowledgeStats: async (): Promise<{
    total_documents: number;
    total_chunks: number;
    total_embeddings: number;
    datasets: string[];
  }> => {
    const res = await fetch(`${API_BASE}/knowledge-base/stats`);
    return handleResponse<any>(res);
  },

  searchKnowledgeBase: async (query: string, top_k = 4, dataset?: string): Promise<{
    query: string;
    total_found: number;
    results: RetrievedChunk[];
  }> => {
    const res = await fetch(`${API_BASE}/knowledge-base/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k, dataset }),
    });
    return handleResponse<any>(res);
  },

  ingestDocument: async (payload: {
    dataset: string;
    title: string;
    content: string;
    source?: string;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE}/knowledge-base/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  getDataSources: async (): Promise<DataSourceItem[]> => {
    const res = await fetch(`${API_BASE}/data-sources`);
    return handleResponse<DataSourceItem[]>(res);
  },

  reindexDataSource: async (name: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/data-sources/${name}/reindex`, {
      method: 'POST',
    });
    return handleResponse<any>(res);
  },

  // --- System Status ---
  getSystemStatus: async (): Promise<SystemStatusData> => {
    const res = await fetch(`${API_BASE}/system/status`);
    return handleResponse<SystemStatusData>(res);
  },

  // --- Settings ---
  getSettings: async (): Promise<SystemSettingsConfig> => {
    const res = await fetch(`${API_BASE}/settings`);
    return handleResponse<SystemSettingsConfig>(res);
  },

  updateSettings: async (settings: Partial<SystemSettingsConfig>): Promise<SystemSettingsConfig> => {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    return handleResponse<SystemSettingsConfig>(res);
  },

  resetSettings: async (): Promise<SystemSettingsConfig> => {
    const res = await fetch(`${API_BASE}/settings/reset`, {
      method: 'POST',
    });
    return handleResponse<SystemSettingsConfig>(res);
  },
};
