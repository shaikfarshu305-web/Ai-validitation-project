import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  ShieldCheck,
  Layers,
  AlertTriangle,
  Award,
  RefreshCw,
  Percent
} from 'lucide-react';
import { api } from '../services/api';
import { TrendLineChart, DimensionComparisonBarChart, VerdictDistributionDonutChart } from '../components/Charts';

export const VerificationInsights: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadInsights = async () => {
    setLoading(true);
    try {
      const res = await api.getVerificationInsights();
      setData(res);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInsights();
  }, []);

  const overview = data?.overview;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Verification Insights & Quality Analytics
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Deep dimensional telemetry, benchmark alignment, and hallucination reduction trends.
          </p>
        </div>

        <button
          onClick={loadInsights}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Analytics
        </button>
      </div>

      {/* KPI Highlight Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Pass Rate</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-3xl font-black text-emerald-700">{overview?.pass_rate ?? 0}%</span>
          </div>
          <span className="text-[10px] text-[#9E775F] mt-1 block">Enterprise target: &gt;80%</span>
        </div>

        <div className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider block">Hallucination Frequency</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-3xl font-black text-rose-700">{overview?.hallucination_frequency ?? 0}%</span>
          </div>
          <span className="text-[10px] text-[#9E775F] mt-1 block">Threshold: &lt;15%</span>
        </div>

        <div className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase tracking-wider block">Avg Completeness</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-3xl font-black text-[#2A1B14]">{overview?.average_completeness?.toFixed(1) ?? '0.0'}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 5.0</span>
          </div>
          <span className="text-[10px] text-[#9E775F] mt-1 block">Coverage of all inquiry clauses</span>
        </div>

        <div className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase tracking-wider block">Avg Accuracy</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-3xl font-black text-emerald-800">{overview?.average_accuracy?.toFixed(1) ?? '0.0'}</span>
            <span className="text-xs font-bold text-[#9E775F]">/ 5.0</span>
          </div>
          <span className="text-[10px] text-[#9E775F] mt-1 block">Grounded truth correlation</span>
        </div>
        <div className="bg-white rounded-3xl p-5 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider block">Confirmed Hallucinations</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-3xl font-black text-rose-800">{overview?.average_hallucination_percentage ?? 0}%</span>
          </div>
          <span className="text-[10px] text-[#9E775F] mt-1 block">Average contradicted claims</span>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft">
          <div className="mb-4">
            <h3 className="text-base font-bold text-[#2A1B14]">Overall Score Progression</h3>
            <p className="text-xs text-[#7D543E]">Score trajectory across historical verification runs</p>
          </div>
          <TrendLineChart data={overview?.score_trend || []} />
        </div>

        <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft">
          <div className="mb-4">
            <h3 className="text-base font-bold text-[#2A1B14]">Verdict Distribution</h3>
            <p className="text-xs text-[#7D543E]">Pass vs Needs Improvement vs Fail ratios</p>
          </div>
          <VerdictDistributionDonutChart
            distribution={overview?.verdict_distribution || { PASS: 0, NEEDS_IMPROVEMENT: 0, FAIL: 0 }}
          />
        </div>
      </div>

      {/* Hallucination Risk Tier Breakdown */}
      <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft space-y-4">
        <div>
          <h3 className="text-base font-bold text-[#2A1B14]">Hallucination Risk Distribution</h3>
          <p className="text-xs text-[#7D543E]">Categorization of responses into Low, Medium, and High Hallucination Risk</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
            <span className="font-bold text-emerald-800 uppercase text-[10px] block">Low Risk (Grounded)</span>
            <span className="text-2xl font-black text-emerald-900 mt-1 block">
              {data?.hallucination_distribution?.['Low Risk (Grounded)'] ?? 0}
            </span>
            <p className="text-emerald-700 text-[11px] mt-1">No claims classified as contradicted.</p>
          </div>

          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200">
            <span className="font-bold text-amber-800 uppercase text-[10px] block">Medium Risk (Partial)</span>
            <span className="text-2xl font-black text-amber-900 mt-1 block">
              {data?.hallucination_distribution?.['Medium Risk (Partial)'] ?? 0}
            </span>
            <p className="text-amber-700 text-[11px] mt-1">Contains unverified or extrapolated assertions.</p>
          </div>

          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
            <span className="font-bold text-rose-800 uppercase text-[10px] block">High Risk (Contradicted)</span>
            <span className="text-2xl font-black text-rose-900 mt-1 block">
              {data?.hallucination_distribution?.['High Risk (Contradicted)'] ?? 0}
            </span>
            <p className="text-rose-700 text-[11px] mt-1">Directly contradicts verified facts (Override Triggered).</p>
          </div>
        </div>
      </div>

      <div className="bg-[#FAF7F2] rounded-3xl p-6 border border-[#E8DFC8] flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#8C5E3C]">System Compliance Snapshot</span>
          <h4 className="text-sm font-bold text-[#2A1B14] mt-0.5">
            AI Validation Engine Status
          </h4>
          <p className="text-xs text-[#5C3D2E] mt-1">
            The system integrates retrieval, multi-agent evaluation, and verdict synthesis into a modular validation workflow for consistent assessment.
          </p>
        </div>
        <div className="px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] text-emerald-800 font-black text-xs shrink-0 flex items-center gap-1.5 shadow-2xs">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Modular Validation Flow
        </div>
      </div>
    </div>
  );
};
