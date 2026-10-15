import React, { useState } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Loader2,
  FileDown
} from 'lucide-react';
import { api } from '../services/api';
import { BatchStatus, BatchRecordItem } from '../types/evaluation';
import { VerdictBadge } from '../components/VerdictBadge';

interface Props {
  onViewEvaluation: (id: string) => void;
}

export const BatchVerify: React.FC<Props> = ({ onViewEvaluation }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    batch_id: string;
    filename: string;
    total_records: number;
    valid_records: number;
    invalid_records: number;
    sample_preview: any[];
  } | null>(null);

  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pagination & filter
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [filterVerdict, setFilterVerdict] = useState('ALL');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a CSV file first.');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadBatchCSV(file);
      setUploadResult(res);
      setBatchStatus(null);
    } catch (err: any) {
      setError(err.message || 'CSV upload and validation failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!uploadResult) return;
    setEvaluating(true);
    setError(null);
    try {
      const res = await api.runBatchEvaluation(uploadResult.batch_id);
      setBatchStatus(res);
    } catch (err: any) {
      setError(err.message || 'Batch verification failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const allRecords = batchStatus?.records || [];
  const filteredRecords = allRecords.filter((r) => {
    if (filterVerdict === 'ALL') return true;
    return r.verdict === filterVerdict;
  });

  const totalPages = Math.ceil(filteredRecords.length / pageSize) || 1;
  const paginatedRecords = filteredRecords.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Batch Verification
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Upload CSV datasets to run bulk 4-dimension verification with real-time row validation.
          </p>
        </div>

        <a
          href={api.getSampleCSVUrl()}
          download="ai_validation_sample_batch.csv"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <Download className="w-3.5 h-3.5" />
          Download Sample CSV
        </a>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-2.5 text-xs">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Box */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-dashed border-[#C9B59F] hover:border-[#8C5E3C] transition-all text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-[#F7F3EB] text-[#5C3D2E] flex items-center justify-center">
          <UploadCloud className="w-7 h-7" />
        </div>

        <div>
          <h3 className="text-sm font-bold text-[#2A1B14]">
            {file ? file.name : 'Choose or Drag & Drop a CSV File'}
          </h3>
          <p className="text-xs text-[#7D543E] mt-1">
            Columns: <code className="bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[#5C3D2E]">question</code>, <code className="bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[#5C3D2E]">ai_response</code> (required), <code className="bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[#9E775F]">reference_answer</code>, <code className="bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[#9E775F]">source_information</code>
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <label className="px-4 py-2 rounded-xl bg-[#FAF7F2] hover:bg-[#EDE3D5] text-[#5C3D2E] border border-[#E4D7C5] text-xs font-bold transition-all cursor-pointer">
            Select File
            <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
          </label>
          {file && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="px-5 py-2 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-bold shadow-soft transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
              {uploading ? 'Validating CSV...' : 'Validate & Stage CSV'}
            </button>
          )}
        </div>
      </div>

      {/* Validation Summary Card */}
      {uploadResult && (
        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-[#F1ECE2]">
            <div>
              <span className="text-[11px] font-bold text-[#7D543E] uppercase tracking-wider">CSV Pre-Flight Inspection</span>
              <h3 className="text-base font-extrabold text-[#2A1B14]">{uploadResult.filename}</h3>
            </div>
            <button
              onClick={handleRunEvaluation}
              disabled={evaluating || uploadResult.valid_records === 0}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#5C3D2E] to-[#3F281D] hover:from-[#4A3024] hover:to-[#2A1B14] text-white text-xs font-black shadow-soft transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {evaluating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {evaluating ? 'Running Multi-Agent Batch...' : `Verify ${uploadResult.valid_records} Valid Records`}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
              <span className="text-[10px] font-bold text-[#7D543E] uppercase">Total Records</span>
              <p className="text-xl font-black text-[#2A1B14] mt-1">{uploadResult.total_records}</p>
            </div>
            <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200">
              <span className="text-[10px] font-bold text-emerald-800 uppercase">Valid Records</span>
              <p className="text-xl font-black text-emerald-800 mt-1">{uploadResult.valid_records}</p>
            </div>
            <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200">
              <span className="text-[10px] font-bold text-amber-800 uppercase">Invalid Records</span>
              <p className="text-xl font-black text-amber-800 mt-1">{uploadResult.invalid_records}</p>
            </div>
          </div>

          {/* Sample preview */}
          <div>
            <span className="text-xs font-bold text-[#5C3D2E] block mb-2">Sample Preview:</span>
            <div className="space-y-1.5">
              {uploadResult.sample_preview.map((sp, i) => (
                <div key={i} className="p-3 rounded-xl bg-[#FCFAF6] border border-[#E8DFC8] flex items-center justify-between text-xs">
                  <div className="truncate max-w-[70%]">
                    <span className="font-bold text-[#2A1B14] mr-2">#{sp.row_index}</span>
                    <span className="text-[#5C3D2E]">{sp.question}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    sp.status === 'VALID' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                  }`}>
                    {sp.status === 'VALID' ? 'VALID' : sp.error || 'INVALID'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Batch Results & Analytics */}
      {batchStatus && (
        <div className="space-y-6">
          {/* Batch Metrics Header */}
          <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-medium">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#F1ECE2]">
              <div>
                <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Batch Evaluation Complete
                </span>
                <h3 className="text-lg font-black text-[#2A1B14] mt-1">
                  Processed {batchStatus.processed_records} / {batchStatus.valid_records} records
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <a
                  href={api.getExportBatchUrl(batchStatus.batch_id)}
                  className="px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] font-bold text-xs transition-all shadow-2xs flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
                >
                  <FileDown className="w-4 h-4 text-[#8C5E3C]" />
                  Export CSV
                </a>
                <a
                  href={api.getBatchPdfUrl(batchStatus.batch_id)}
                  className="px-4 py-2 rounded-xl bg-[#5C3D2E] text-white font-bold text-xs transition-all shadow-soft flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
                >
                  <FileDown className="w-4 h-4" />
                  Export PDF Report
                </a>
              </div>
            </div>

            {/* Averages Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 mt-4 text-center">
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
                <span className="text-[10px] font-bold text-[#7D543E] uppercase">Avg Overall</span>
                <p className="text-xl font-black text-[#2A1B14] mt-1">{batchStatus.average_overall_score} <span className="text-xs text-[#9E775F]">/ 100</span></p>
              </div>
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
                <span className="text-[10px] font-bold text-emerald-800 uppercase">Avg Accuracy</span>
                <p className="text-xl font-black text-emerald-800 mt-1">{batchStatus.average_accuracy} <span className="text-xs text-[#9E775F]">/ 5</span></p>
              </div>
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
                <span className="text-[10px] font-bold text-[#7D543E] uppercase">Avg Relevance</span>
                <p className="text-xl font-black text-[#7D543E] mt-1">{batchStatus.average_relevance} <span className="text-xs text-[#9E775F]">/ 5</span></p>
              </div>
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
                <span className="text-[10px] font-bold text-amber-800 uppercase">Avg Complete</span>
                <p className="text-xl font-black text-amber-800 mt-1">{batchStatus.average_completeness} <span className="text-xs text-[#9E775F]">/ 5</span></p>
              </div>
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
                <span className="text-[10px] font-bold text-rose-800 uppercase">Avg Safety</span>
                <p className="text-xl font-black text-rose-800 mt-1">{(batchStatus.average_hallucination_score * 2).toFixed(1)} <span className="text-xs text-[#9E775F]">/ 10</span></p>
              </div>
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200">
                <span className="text-[10px] font-bold text-rose-800 uppercase">Hallucination %</span>
                <p className="text-xl font-black text-rose-800 mt-1">{batchStatus.average_hallucination_percentage}%</p>
              </div>
              <div className="p-3 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] col-span-2 sm:col-span-1">
                <span className="text-[10px] font-bold text-rose-800 uppercase">Halluc Freq</span>
                <p className="text-xl font-black text-rose-800 mt-1">{batchStatus.hallucination_frequency}%</p>
              </div>
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
            <div className="p-5 border-b border-[#E4D7C5] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">Batch Records Table</h3>
                <p className="text-xs text-[#7D543E]">Click "View" on any row to open full 4-dimension report</p>
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#7D543E]">Verdict:</span>
                <select
                  value={filterVerdict}
                  onChange={(e) => {
                    setFilterVerdict(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-1.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-xs font-semibold text-[#2A1B14]"
                >
                  <option value="ALL">All Verdicts</option>
                  <option value="PASS">Pass</option>
                  <option value="NEEDS_IMPROVEMENT">Needs Improvement</option>
                  <option value="FAIL">Fail</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#FAF7F2] border-b border-[#E4D7C5] text-[#7D543E] font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-3 text-center">Row</th>
                    <th className="py-3 px-4">Question</th>
                    <th className="py-3 px-3 text-center">Accuracy</th>
                    <th className="py-3 px-3 text-center">Relevance</th>
                    <th className="py-3 px-3 text-center">Safety / 10</th>
                    <th className="py-3 px-3 text-center">Complete</th>
                    <th className="py-3 px-3 text-center">Score</th>
                    <th className="py-3 px-4 text-center">Verdict</th>
                    <th className="py-3 px-4 text-right">View</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1ECE2]">
                  {paginatedRecords.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-xs text-[#9E775F]">
                        No records match the selected filter.
                      </td>
                    </tr>
                  ) : (
                    paginatedRecords.map((r) => (
                      <tr key={r.id} className="hover:bg-[#FCFAF6] transition-colors">
                        <td className="py-3.5 px-3 text-center font-bold text-[#9E775F]">#{r.row_index}</td>
                        <td className="py-3.5 px-4 font-semibold text-[#2A1B14] max-w-[260px] truncate" title={r.question}>
                          {r.question}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-emerald-800">
                          {r.accuracy_score?.toFixed(1) ?? '-'}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-[#7D543E]">
                          {r.relevance_score?.toFixed(1) ?? '-'}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-rose-800">
                          {r.hallucination_score != null ? (r.hallucination_score * 2).toFixed(1) : '-'}
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-amber-800">
                          {r.completeness_score?.toFixed(1) ?? '-'}
                        </td>
                        <td className="py-3.5 px-3 text-center font-black text-sm text-[#2A1B14]">
                          {r.overall_score ?? '-'}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {r.verdict ? <VerdictBadge verdict={r.verdict} size="sm" /> : <span className="text-[10px] text-[#9E775F]">{r.status}</span>}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {r.evaluation_id ? (
                            <button
                              onClick={() => onViewEvaluation(r.evaluation_id!)}
                              className="px-2.5 py-1 rounded-lg bg-[#FAF7F2] hover:bg-[#EDE3D5] text-[#5C3D2E] font-bold text-xs border border-[#E4D7C5] transition-all cursor-pointer"
                            >
                              View
                            </button>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-[#E4D7C5] flex items-center justify-between text-xs">
                <span className="text-[#7D543E]">
                  Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filteredRecords.length)} of {filteredRecords.length}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="px-3 py-1 rounded-lg border border-[#E4D7C5] bg-[#FAF7F2] disabled:opacity-40 text-[#5C3D2E] font-bold cursor-pointer"
                  >
                    Prev
                  </button>
                  <span className="px-2 font-bold text-[#2A1B14]">
                    {page} / {totalPages}
                  </span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="px-3 py-1 rounded-lg border border-[#E4D7C5] bg-[#FAF7F2] disabled:opacity-40 text-[#5C3D2E] font-bold cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
