import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  Filter,
  ExternalLink,
  Trash2,
  RefreshCw,
  Calendar,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { EvaluationListItem } from '../types/evaluation';
import { VerdictBadge } from '../components/VerdictBadge';

interface Props {
  onViewEvaluation: (id: string) => void;
}

export const EvaluationHistory: React.FC<Props> = ({ onViewEvaluation }) => {
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [verdict, setVerdict] = useState('ALL');
  const [hallucinationStatus, setHallucinationStatus] = useState('ALL');
  const [minScore, setMinScore] = useState<number>(0);
  const [maxScore, setMaxScore] = useState<number>(100);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await api.listEvaluations({
        search: search.trim() || undefined,
        verdict: verdict !== 'ALL' ? verdict : undefined,
        hallucination_status: hallucinationStatus !== 'ALL' ? hallucinationStatus : undefined,
        min_score: minScore > 0 ? minScore : undefined,
        max_score: maxScore < 100 ? maxScore : undefined,
      });
      setEvaluations(data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [verdict, hallucinationStatus]);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistory();
  };

  const handleResetFilters = () => {
    setSearch('');
    setVerdict('ALL');
    setHallucinationStatus('ALL');
    setMinScore(0);
    setMaxScore(100);
    setTimeout(fetchHistory, 50);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Evaluation History
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Auditable log of all verified AI responses, dimensional scores, and verdicts.
          </p>
        </div>

        <button
          onClick={fetchHistory}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh List
        </button>
      </div>

      {/* Filter Controls Bar */}
      <form
        onSubmit={handleApplyFilter}
        className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-soft space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Search Question */}
          <div>
            <label className="font-semibold text-[#5C3D2E] block mb-1">Search Question</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#9E775F] absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter by question text..."
                className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] focus:outline-hidden"
              />
            </div>
          </div>

          {/* Verdict Filter */}
          <div>
            <label className="font-semibold text-[#5C3D2E] block mb-1">Verdict Status</label>
            <select
              value={verdict}
              onChange={(e) => setVerdict(e.target.value)}
              className="w-full p-1.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-semibold"
            >
              <option value="ALL">All Verdicts</option>
              <option value="PASS">PASS</option>
              <option value="NEEDS_IMPROVEMENT">NEEDS IMPROVEMENT</option>
              <option value="FAIL">FAIL</option>
            </select>
          </div>

          {/* Hallucination Risk Filter */}
          <div>
            <label className="font-semibold text-[#5C3D2E] block mb-1">Hallucination Risk</label>
            <select
              value={hallucinationStatus}
              onChange={(e) => setHallucinationStatus(e.target.value)}
              className="w-full p-1.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-semibold"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="LOW">LOW Risk (Grounded)</option>
              <option value="MEDIUM">MEDIUM Risk (Partial)</option>
              <option value="HIGH">HIGH Risk (Contradicted)</option>
            </select>
          </div>

          {/* Score Range */}
          <div>
            <label className="font-semibold text-[#5C3D2E] block mb-1">Min Score: {minScore}</label>
            <input
              type="range"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full accent-[#5C3D2E]"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#F1ECE2]">
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-3.5 py-1.5 rounded-xl border border-[#E4D7C5] text-[#5C3D2E] text-xs font-bold hover:bg-[#FAF7F2] cursor-pointer"
          >
            Reset
          </button>
          <button
            type="submit"
            className="px-4 py-1.5 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-bold shadow-soft cursor-pointer"
          >
            Apply Filters
          </button>
        </div>
      </form>

      {/* History Table */}
      <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
        <div className="p-5 border-b border-[#E4D7C5] flex items-center justify-between">
          <h3 className="text-base font-bold text-[#2A1B14]">
            Evaluations ({evaluations.length})
          </h3>
          <span className="text-xs text-[#7D543E]">Sorted chronologically</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#FAF7F2] border-b border-[#E4D7C5] text-[#7D543E] font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3.5 px-4">Question</th>
                <th className="py-3.5 px-3 text-center">Score</th>
                <th className="py-3.5 px-3 text-center">Accuracy</th>
                <th className="py-3.5 px-3 text-center">Relevance</th>
                <th className="py-3.5 px-3 text-center">Halluc</th>
                <th className="py-3.5 px-3 text-center">Complete</th>
                <th className="py-3.5 px-4 text-center">Verdict</th>
                <th className="py-3.5 px-4">Date</th>
                <th className="py-3.5 px-4 text-right">View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1ECE2]">
              {evaluations.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-xs text-[#9E775F]">
                    No evaluation records match the selected filters.
                  </td>
                </tr>
              ) : (
                evaluations.map((row) => (
                  <tr key={row.id} className="hover:bg-[#FCFAF6] transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-[#2A1B14] max-w-[280px] truncate" title={row.question}>
                      {row.question}
                    </td>
                    <td className="py-3.5 px-3 text-center font-black text-sm text-[#2A1B14]">
                      {row.overall_score}
                    </td>
                    <td className="py-3.5 px-3 text-center font-bold text-emerald-800">
                      {row.accuracy.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-3 text-center font-bold text-[#7D543E]">
                      {row.relevance.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-3 text-center font-bold text-rose-800">
                      {row.hallucination.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-3 text-center font-bold text-amber-800">
                      {row.completeness.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <VerdictBadge verdict={row.verdict} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-[11px] text-[#9E775F]">
                      {row.created_at}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => onViewEvaluation(row.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-[#FAF7F2] hover:bg-[#EDE3D5] text-[#5C3D2E] font-bold text-xs border border-[#E4D7C5] transition-all cursor-pointer"
                      >
                        View
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
