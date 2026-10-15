import React, { useState, useEffect } from 'react';
import {
  FileText,
  Printer,
  Download,
  Search,
  CheckCircle2,
  AlertTriangle,
  Award,
  Layers,
  ShieldAlert,
  Target
} from 'lucide-react';
import { api } from '../services/api';
import { EvaluationListItem, EvaluationDetail } from '../types/evaluation';
import { VerdictBadge } from '../components/VerdictBadge';
import { ClaimBadge } from '../components/ClaimBadge';

export const Reports: React.FC = () => {
  const [list, setList] = useState<EvaluationListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reportData, setReportData] = useState<EvaluationDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listEvaluations().then((data) => {
      setList(data);
      if (data.length > 0) {
        setSelectedId(data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedId) {
      setLoading(true);
      api.getEvaluationDetail(selectedId).then((res) => {
        setReportData(res);
        setLoading(false);
      });
    }
  }, [selectedId]);

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    if (!reportData) return;
    const reportText = `
========================================================================
AI RESPONSE VALIDATION REPORT
Academic Evaluation Summary
========================================================================

Evaluation ID: ${reportData.id}
Date: ${reportData.created_at}
Overall Score: ${reportData.overall_score} / 100
Final Verdict: ${reportData.verdict}

------------------------------------------------------------------------
PROMPT & AI RESPONSE
------------------------------------------------------------------------
Question:
${reportData.question}

AI Response:
${reportData.ai_response}

Ground Truth Reference:
${reportData.reference_answer || 'None provided'}

------------------------------------------------------------------------
FOUR EVALUATION DIMENSIONS
------------------------------------------------------------------------
1. Factual Accuracy: ${reportData.accuracy_score} / 5.0 (Weight ${Math.round((reportData.verdict_details?.weights?.accuracy ?? 0.30) * 100)}%)
Reasoning: ${reportData.accuracy_details?.reasoning || 'N/A'}

2. Hallucination Safety: ${(reportData.hallucination_score * 2).toFixed(1)} / 10.0 (Weight ${Math.round((reportData.verdict_details?.weights?.hallucination_safety ?? 0.25) * 100)}%)
Status: ${reportData.hallucination_details?.hallucination_status || 'LOW'}
Hallucination Percentage (verified contradicted claims): ${reportData.hallucination_percentage}%
Reasoning: ${reportData.hallucination_details?.reasoning || 'N/A'}

3. Prompt Relevance: ${reportData.relevance_score} / 5.0 (Weight ${Math.round((reportData.verdict_details?.weights?.relevance ?? 0.25) * 100)}%)
Reasoning: ${reportData.relevance_details?.reasoning || 'N/A'}

4. Completeness: ${reportData.completeness_score} / 5.0 (Weight ${Math.round((reportData.verdict_details?.weights?.completeness ?? 0.20) * 100)}%)
Reasoning: ${reportData.completeness_details?.reasoning || 'N/A'}

------------------------------------------------------------------------
EXECUTIVE VERDICT SUMMARY
------------------------------------------------------------------------
${reportData.summary || 'N/A'}

Major Issues:
${reportData.major_issues.map((iss) => `- ${iss}`).join('\n') || '- None'}

Recommendations:
${reportData.recommendations.map((rec) => `- ${rec}`).join('\n') || '- Meets enterprise criteria'}
========================================================================
    `.trim();

    const element = document.createElement('a');
    const file = new Blob([reportText], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `ai_validation_report_${reportData.id.slice(0, 8)}.txt`;
    document.body.appendChild(element);
    element.click();
    element.remove();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 no-print">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Verification Reports
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Generate, print, or download enterprise-grade audit reports for evaluated AI responses.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            disabled={!reportData}
            className="px-3.5 py-1.5 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            Download Text
          </button>
          <button
            onClick={handlePrint}
            disabled={!reportData}
            className="px-4 py-1.5 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-extrabold shadow-soft transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / PDF Report
          </button>
        </div>
      </div>

      {/* Selector dropdown for report */}
      <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs flex flex-col sm:flex-row sm:items-center gap-3 text-xs no-print">
        <span className="font-bold text-[#5C3D2E] shrink-0">Select Evaluation to View Report:</span>
        <select
          value={selectedId || ''}
          onChange={(e) => setSelectedId(e.target.value)}
          className="flex-1 p-2 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-semibold"
        >
          {list.map((item) => (
            <option key={item.id} value={item.id}>
              [{item.verdict}] {item.question.slice(0, 80)}... ({item.overall_score}/100)
            </option>
          ))}
        </select>
      </div>

      {/* Printable Report Canvas */}
      {reportData && (
        <div className="bg-white rounded-3xl p-8 sm:p-10 border border-[#E4D7C5] shadow-medium space-y-8 print:border-none print:shadow-none print:p-0">
          {/* Formal Letterhead */}
          <div className="border-b-2 border-[#5C3D2E] pb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-7 h-7 rounded-lg bg-[#5C3D2E] text-white flex items-center justify-center font-black text-xs">
                  AI
                </span>
                <h1 className="text-xl font-black text-[#2A1B14] tracking-wider uppercase">
                  AI VALIDATION REPORT
                </h1>
              </div>
              <p className="text-xs text-[#7D543E] font-medium">
                AI Response Evaluation and Validation Summary
              </p>
            </div>

            <div className="text-left sm:text-right text-xs space-y-1">
              <p className="font-mono text-[#5C3D2E] font-semibold">Report ID: {reportData.id}</p>
              <p className="text-[#7D543E]">Date: {reportData.created_at.slice(0, 10)}</p>
              <div className="inline-block mt-1">
                <VerdictBadge verdict={reportData.verdict} size="md" />
              </div>
            </div>
          </div>

          {/* Executive Score Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
              <span className="text-[10px] font-bold text-[#7D543E] uppercase block">Overall Score</span>
              <span className="text-2xl font-black text-[#2A1B14] mt-1 block">{reportData.overall_score} <span className="text-xs text-[#9E775F]">/ 100</span></span>
            </div>
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
              <span className="text-[10px] font-bold text-emerald-800 uppercase block">Factual Accuracy</span>
              <span className="text-2xl font-black text-emerald-800 mt-1 block">{reportData.accuracy_score.toFixed(1)} <span className="text-xs text-emerald-600">/ 5</span></span>
            </div>
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
              <span className="text-[10px] font-bold text-rose-800 uppercase block">Hallucination Safety</span>
              <span className="text-2xl font-black text-rose-800 mt-1 block">{(reportData.hallucination_score * 2).toFixed(1)} <span className="text-xs text-rose-600">/ 10</span></span>
              <span className="text-xs font-semibold text-rose-700 block mt-1">{reportData.hallucination_percentage.toFixed(1)}% contradicted claims</span>
            </div>
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200">
              <span className="text-[10px] font-bold text-amber-800 uppercase block">Completeness</span>
              <span className="text-2xl font-black text-amber-800 mt-1 block">{reportData.completeness_score.toFixed(1)} <span className="text-xs text-amber-600">/ 5</span></span>
            </div>
          </div>

          {/* Submission Details */}
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
              <h4 className="font-bold text-[#5C3D2E] uppercase text-[10px] tracking-wider mb-1">
                Prompt / Question:
              </h4>
              <p className="font-semibold text-[#2A1B14] text-sm">{reportData.question}</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
              <h4 className="font-bold text-[#5C3D2E] uppercase text-[10px] tracking-wider mb-1">
                Evaluated AI Response:
              </h4>
              <p className="text-[#3F281D] leading-relaxed whitespace-pre-wrap">{reportData.ai_response}</p>
            </div>

            {reportData.reference_answer && (
              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200">
                <h4 className="font-bold text-emerald-800 uppercase text-[10px] tracking-wider mb-1">
                  Ground Truth Reference Benchmark:
                </h4>
                <p className="text-emerald-950">{reportData.reference_answer}</p>
              </div>
            )}
          </div>

          {/* Flagged Claims Breakdown */}
          {reportData.hallucination_details?.flagged_claims && reportData.hallucination_details.flagged_claims.length > 0 && (
            <div className="space-y-3 text-xs">
              <h4 className="font-bold text-[#2A1B14] uppercase text-xs tracking-wider border-b border-[#F1ECE2] pb-2">
                Claim-Level Hallucination Verification:
              </h4>
              <div className="space-y-2">
                {reportData.hallucination_details.flagged_claims.map((claim, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#2A1B14]">Statement #{idx + 1}</span>
                      <ClaimBadge status={claim.status} />
                    </div>
                    <p className="italic text-[#2A1B14]">"{claim.claim}"</p>
                    <p className="text-[#5C3D2E]"><strong>Reasoning:</strong> {claim.reasoning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Executive Summary & Recommendations */}
          <div className="space-y-4 text-xs pt-4 border-t border-[#F1ECE2]">
            <h4 className="font-bold text-[#2A1B14] uppercase text-xs tracking-wider">
              Executive Evaluation Summary:
            </h4>
            <p className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8] text-[#2A1B14] leading-relaxed">
              {reportData.summary}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-rose-50/60 border border-rose-200 space-y-1.5">
                <span className="font-bold text-rose-800 uppercase text-[10px]">Identified Deficiencies:</span>
                <ul className="list-disc list-inside space-y-1 text-rose-950 font-medium">
                  {reportData.major_issues.map((iss, i) => (
                    <li key={i}>{iss}</li>
                  ))}
                  {reportData.major_issues.length === 0 && <li>None detected.</li>}
                </ul>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-200 space-y-1.5">
                <span className="font-bold text-emerald-800 uppercase text-[10px]">Recommendations:</span>
                <ul className="list-disc list-inside space-y-1 text-emerald-950 font-medium">
                  {reportData.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Signature / Certification Footer */}
          <div className="pt-8 border-t border-[#5C3D2E] flex items-center justify-between text-[11px] text-[#7D543E]">
            <span>AI Validation Multi-Agent Evaluation Engine</span>
            <span>Verified & Authenticated</span>
          </div>
        </div>
      )}
    </div>
  );
};
