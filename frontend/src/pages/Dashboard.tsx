import React, { useEffect, useState } from 'react';
import {
  FileCheck2,
  Award,
  Target,
  CheckCircle,
  Layers,
  ShieldAlert,
  Percent,
  ArrowUpRight,
  RefreshCw,
  Search,
  ExternalLink
} from 'lucide-react';
import { DashboardOverview, EvaluationListItem } from '../types/evaluation';
import { api } from '../services/api';
import { VerdictBadge } from '../components/VerdictBadge';
import { TrendLineChart, DimensionComparisonBarChart, VerdictDistributionDonutChart } from '../components/Charts';

interface Props {
  onViewEvaluation: (id: string) => void;
  onNavigateToVerify: () => void;
}

export const Dashboard: React.FC<Props> = ({ onViewEvaluation, onNavigateToVerify }) => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableSearch, setTableSearch] = useState('');
  const [filters, setFilters] = useState({
    verdict: 'ALL',
    minScore: '',
    maxScore: '',
    batchId: '',
    status: 'ALL',
    hallucination: 'ALL',
  });

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDashboardOverview({
        verdict: filters.verdict !== 'ALL' ? filters.verdict : undefined,
        min_score: filters.minScore ? Number(filters.minScore) : undefined,
        max_score: filters.maxScore ? Number(filters.maxScore) : undefined,
        batch_id: filters.batchId || undefined,
        evaluation_status: filters.status !== 'ALL' ? filters.status : undefined,
        hallucination_presence: filters.hallucination !== 'ALL' ? filters.hallucination : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, [filters.verdict, filters.minScore, filters.maxScore, filters.batchId, filters.status, filters.hallucination]);

  const filteredRecent = (data?.recent_evaluations || []).filter((item) =>
    item.question.toLowerCase().includes(tableSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-3xl p-4 border border-[#E4D7C5] shadow-soft">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-3">
          <select value={filters.verdict} onChange={(e) => setFilters((prev) => ({ ...prev, verdict: e.target.value }))} className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]">
            <option value="ALL">All verdicts</option>
            <option value="PASS">PASS</option>
            <option value="NEEDS_IMPROVEMENT">NEEDS_IMPROVEMENT</option>
            <option value="FAIL">FAIL</option>
          </select>
          <input value={filters.minScore} onChange={(e) => setFilters((prev) => ({ ...prev, minScore: e.target.value }))} type="number" min={0} max={100} placeholder="Min score" className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]" />
          <input value={filters.maxScore} onChange={(e) => setFilters((prev) => ({ ...prev, maxScore: e.target.value }))} type="number" min={0} max={100} placeholder="Max score" className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]" />
          <input value={filters.batchId} onChange={(e) => setFilters((prev) => ({ ...prev, batchId: e.target.value }))} placeholder="Batch ID" className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]" />
          <select value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))} className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]">
            <option value="ALL">All statuses</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="PROCESSING">PROCESSING</option>
          </select>
          <select value={filters.hallucination} onChange={(e) => setFilters((prev) => ({ ...prev, hallucination: e.target.value }))} className="rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] px-3 py-2 text-xs text-[#2A1B14]">
            <option value="ALL">Hallucination: all</option>
            <option value="yes">With hallucination</option>
            <option value="no">Without hallucination</option>
          </select>
        </div>
      </div>
      {/* Welcome Banner */}
      <div className="rounded-3xl bg-gradient-to-r from-[#3F281D] via-[#5C3D2E] to-[#7D543E] p-6 lg:p-8 text-white shadow-medium relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white/10 to-transparent pointer-events-none" />
        <div className="relative z-10 max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-black tracking-tight mb-2">
            AI Response Validation Dashboard
          </h2>
          <p className="text-sm text-[#D9C8B4] leading-relaxed mb-5">
            Automated evaluation of AI responses for relevance, accuracy, hallucination, and completeness.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onNavigateToVerify}
              className="px-4 py-2 rounded-xl bg-white text-[#2A1B14] font-bold text-xs shadow-soft hover:bg-[#F7F3EB] transition-all flex items-center gap-1.5 cursor-pointer"
            >
              Verify Single Response
              <ArrowUpRight className="w-4 h-4 text-[#5C3D2E]" />
            </button>
            <button
              onClick={fetchOverview}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-[#F7F3EB] font-semibold text-xs transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh Data
            </button>
          </div>
        </div>
      </div>

      {/* 7 Key Overview Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 sm:gap-4">
        {/* Total Evaluations */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-[#7D543E] uppercase tracking-wider">Total Evals</span>
            <FileCheck2 className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{data?.total_evaluations ?? 0}</span>
          <span className="text-[10px] text-[#9E775F] font-medium mt-1">Ground truth verified</span>
        </div>

        {/* Average Overall Score */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-[#7D543E] uppercase tracking-wider">Avg Score</span>
            <Award className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-[#2A1B14]">{data?.average_overall_score ?? 0}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 100</span>
          </div>
          <span className="text-[10px] text-[#9E775F] font-medium mt-1">Weighted index</span>
        </div>

        {/* Average Accuracy */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">Accuracy</span>
            <CheckCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-[#2A1B14]">{data?.average_accuracy?.toFixed(1) ?? '0.0'}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 5.0</span>
          </div>
          <span className="text-[10px] text-emerald-700 font-semibold mt-1">Weight 35%</span>
        </div>

        {/* Average Relevance */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-[#7D543E] uppercase tracking-wider">Relevance</span>
            <Target className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-[#2A1B14]">{data?.average_relevance?.toFixed(1) ?? '0.0'}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 5.0</span>
          </div>
          <span className="text-[10px] text-[#7D543E] font-semibold mt-1">Weight 25%</span>
        </div>

        {/* Average Completeness */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">Complete</span>
            <Layers className="w-4 h-4 text-amber-700" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-[#2A1B14]">{data?.average_completeness?.toFixed(1) ?? '0.0'}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 5.0</span>
          </div>
          <span className="text-[10px] text-amber-800 font-semibold mt-1">Weight 15%</span>
        </div>

        {/* Hallucination Frequency */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">Halluc Rate</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{data?.hallucination_frequency ?? 0}%</span>
          <span className="text-[10px] text-rose-700 font-semibold mt-1">High/Med risk claims</span>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">Confirmed Hallucinations</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{data?.average_hallucination_percentage ?? 0}%</span>
          <span className="text-[10px] text-rose-700 font-semibold mt-1">Average contradicted claims</span>
        </div>

        {/* Pass Rate */}
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col justify-between col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">Pass Rate</span>
            <Percent className="w-4 h-4 text-emerald-600" />
          </div>
          <span className="text-2xl font-black text-emerald-700">{data?.pass_rate ?? 0}%</span>
          <span className="text-[10px] text-emerald-800 font-semibold mt-1">Meets threshold</span>
        </div>
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Score Trend Chart */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-[#2A1B14]">Overall Evaluation Score Trend</h3>
              <p className="text-xs text-[#7D543E]">Chronological progression across evaluation runs</p>
            </div>
            <span className="text-xs font-bold text-[#8C5E3C] px-2.5 py-1 rounded-lg bg-[#F7F3EB] border border-[#E4D7C5]">
              Normalized Scale (0-100)
            </span>
          </div>
          <TrendLineChart data={data?.score_trend || []} />
        </div>

        {/* Verdict Distribution */}
        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft flex flex-col justify-between">
          <div className="mb-4">
            <h3 className="text-base font-bold text-[#2A1B14]">Verdict Distribution</h3>
            <p className="text-xs text-[#7D543E]">Breakdown of Pass, Needs Improvement, & Fail</p>
          </div>
          <VerdictDistributionDonutChart
            distribution={data?.verdict_distribution || { PASS: 0, NEEDS_IMPROVEMENT: 0, FAIL: 0 }}
          />
        </div>
      </div>

      {/* Dimension Comparison Bar Section */}
      <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-[#2A1B14]">Dimension Performance Benchmark</h3>
            <p className="text-xs text-[#7D543E]">
              Aggregated percentage performance across the four core evaluation dimensions
            </p>
          </div>
        </div>
        <DimensionComparisonBarChart
          dimensions={
            data?.dimension_comparison || {
              Accuracy: 0,
              Relevance: 0,
              Completeness: 0,
              HallucinationSafety: 0,
            }
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distribution */}
        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft overflow-x-auto">
          <div className="mb-4">
            <h3 className="text-base font-bold text-[#2A1B14]">Score Distribution</h3>
            <p className="text-xs text-[#7D543E]">Count of evaluation scores by range</p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-[#FAF7F2] border-b border-[#E4D7C5] text-[#7D543E] font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-2 px-2">Dimension</th>
                <th className="py-2 px-2 text-center">0-20</th>
                <th className="py-2 px-2 text-center">21-40</th>
                <th className="py-2 px-2 text-center">41-60</th>
                <th className="py-2 px-2 text-center">61-80</th>
                <th className="py-2 px-2 text-center">81-100</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1ECE2]">
              {data?.score_distribution && Object.entries(data.score_distribution).map(([dim, bins]) => (
                <tr key={dim}>
                  <td className="py-2 px-2 font-semibold capitalize text-[#2A1B14]">{dim}</td>
                  <td className="py-2 px-2 text-center text-[#5C3D2E]">{bins['0-20']}</td>
                  <td className="py-2 px-2 text-center text-[#5C3D2E]">{bins['21-40']}</td>
                  <td className="py-2 px-2 text-center text-[#5C3D2E]">{bins['41-60']}</td>
                  <td className="py-2 px-2 text-center text-[#5C3D2E]">{bins['61-80']}</td>
                  <td className="py-2 px-2 text-center text-[#5C3D2E]">{bins['81-100']}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Common Issues */}
        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft">
          <div className="mb-4">
            <h3 className="text-base font-bold text-[#2A1B14]">Common Issues</h3>
            <p className="text-xs text-[#7D543E]">Most frequently occurring evaluation problems</p>
          </div>
          {data?.common_issues && data.common_issues.length > 0 ? (
            <div className="space-y-3">
              {data.common_issues.map((issue, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-[#FAF7F2] border border-[#E8DFC8]">
                  <span className="font-semibold text-xs text-[#2A1B14]">{issue.issue}</span>
                  <span className="font-bold text-[#5C3D2E] text-xs px-2 py-0.5 bg-[#E4D7C5] rounded-full">{issue.count}</span>
                </div>
              ))}
            </div>
          ) : (
             <p className="text-xs text-[#9E775F] italic">No common issues identified yet.</p>
          )}
        </div>
      </div>

      {/* Recent Evaluations Table */}
      <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-[#E4D7C5] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-[#2A1B14]">Recent Evaluations</h3>
            <p className="text-xs text-[#7D543E]">Latest AI response verification runs and verdicts</p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-[#9E775F] absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search recent questions..."
              value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-[#E4D7C5] text-xs bg-[#FAF7F2] text-[#2A1B14] placeholder-[#9E775F] focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#FAF7F2] border-b border-[#E4D7C5] text-[#7D543E] font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3.5 px-4">Question</th>
                <th className="py-3.5 px-3 text-center">Score</th>
                <th className="py-3.5 px-3 text-center">Accuracy</th>
                <th className="py-3.5 px-3 text-center">Relevance</th>
                <th className="py-3.5 px-3 text-center">Hallucination</th>
                <th className="py-3.5 px-3 text-center">Completeness</th>
                <th className="py-3.5 px-4 text-center">Verdict</th>
                <th className="py-3.5 px-4">Date</th>
                <th className="py-3.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1ECE2]">
              {filteredRecent.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-xs text-[#9E775F]">
                    No evaluation records found matching filter.
                  </td>
                </tr>
              ) : (
                filteredRecent.map((row) => (
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
