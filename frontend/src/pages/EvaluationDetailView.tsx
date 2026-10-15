import React, { useState } from 'react';
import {
  ArrowLeft,
  Printer,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  FileText,
  RotateCcw,
  Sparkles,
  Shield,
  ShieldAlert,
  Layers,
  Target
} from 'lucide-react';
import { EvaluationDetail } from '../types/evaluation';
import { ScoreGauge } from '../components/ScoreGauge';
import { VerdictBadge } from '../components/VerdictBadge';
import { DimensionCard } from '../components/DimensionCard';
import { ClaimBadge } from '../components/ClaimBadge';
import { api } from '../services/api';

interface Props {
  evaluation: EvaluationDetail;
  onBack: () => void;
  onEvaluateAnother: () => void;
  onGoToHistory: () => void;
}

export const EvaluationDetailView: React.FC<Props> = ({
  evaluation,
  onBack,
  onEvaluateAnother,
  onGoToHistory,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'relevance' | 'accuracy' | 'hallucination' | 'completeness'>('all');
  const [openSections, setOpenSections] = useState({
    relevance: true,
    accuracy: true,
    hallucination: true,
    completeness: true,
    evidence: true,
    summary: true,
  });

  const toggleSection = (sec: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  const handleDownloadJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(evaluation, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `ai_validation_evaluation_${evaluation.id.slice(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handlePrint = () => {
    window.open(api.getExportEvaluationPdfUrl(evaluation.id), '_blank');
  };

  const rel = evaluation.relevance_details;
  const acc = evaluation.accuracy_details;
  const hal = evaluation.hallucination_details;
  const comp = evaluation.completeness_details;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 no-print">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#5C3D2E] hover:text-[#2A1B14] transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Overview
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleDownloadJSON}
            className="px-3.5 py-1.5 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Download JSON
          </button>
          <button
            onClick={handlePrint}
            className="px-3.5 py-1.5 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / PDF Report
          </button>
          <button
            onClick={onEvaluateAnother}
            className="px-4 py-1.5 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-extrabold shadow-soft transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Verify Another
          </button>
        </div>
      </div>

      {/* Main Verdict & Score Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-medium">
        {acc?.factual_consistency === 'UNSUPPORTED' && !evaluation.reference_answer && !evaluation.source_information && evaluation.retrieved_evidence.length === 0 && (
          <div className="mb-5 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-xs">
            <strong className="block mb-1">Factual answer unverified</strong>
            <span>The score is conservative because no reference or relevant knowledge evidence was available. It does not mean the answer was proven wrong. Add a reference answer or source document to verify it.</span>
          </div>
        )}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-[#F1ECE2]">
          <div className="space-y-3 text-center md:text-left flex-1">
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-2">
              <span className="text-[11px] font-bold text-[#7D543E] uppercase tracking-wider">
                Evaluation Report
              </span>
              <span className="text-xs text-[#9E775F]">•</span>
              <span className="font-mono text-xs text-[#7D543E]">ID: {evaluation.id.slice(0, 13)}...</span>
              <span className="text-xs text-[#9E775F]">•</span>
              <span className="text-xs text-[#9E775F]">{evaluation.created_at.slice(0, 16).replace('T', ' ')}</span>
            </div>

            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
              <h2 className="text-2xl sm:text-3xl font-black text-[#2A1B14] tracking-tight">
                Final Verdict:
              </h2>
              <VerdictBadge verdict={evaluation.verdict} size="lg" />
            </div>

            <p className="text-xs sm:text-sm text-[#5C3D2E] leading-relaxed max-w-2xl">
              {evaluation.summary || 'Comprehensive multi-agent evaluation completed.'}
            </p>
          </div>

          {/* Large Overall Score Gauge */}
          <div className="shrink-0 p-3 rounded-2xl bg-[#FCFAF6] border border-[#E4D7C5]">
            <ScoreGauge score={evaluation.overall_score} size={150} strokeWidth={12} />
          </div>
        </div>

        {/* Question & AI Response Snippet */}
        <div className="mt-6 space-y-3 text-xs">
          <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8]">
            <span className="font-bold text-[#7D543E] uppercase tracking-wider text-[10px] block mb-1">
              Submitted Question:
            </span>
            <p className="font-semibold text-[#2A1B14]">{evaluation.question}</p>
          </div>

          <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
            <span className="font-bold text-[#7D543E] uppercase tracking-wider text-[10px] block mb-1">
              Evaluated AI Response:
            </span>
            <p className="text-[#3F281D] leading-relaxed whitespace-pre-wrap">{evaluation.ai_response}</p>
          </div>

          {evaluation.reference_answer && (
            <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200">
              <span className="font-bold text-emerald-800 uppercase tracking-wider text-[10px] block mb-1">
                Verified Ground Truth Reference:
              </span>
              <p className="text-emerald-950 font-medium">{evaluation.reference_answer}</p>
            </div>
          )}
        </div>
      </div>

      {/* 4 Major Dimension Score Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DimensionCard
          dimension="accuracy"
          title="Factual Accuracy"
          score={evaluation.accuracy_score}
          description={acc?.reasoning || 'Evaluates factual truth grounded on reference and RAG chunks.'}
          weight={evaluation.verdict_details?.weights?.accuracy ?? 0.30}
          isActive={activeTab === 'accuracy'}
          onClick={() => setActiveTab(activeTab === 'accuracy' ? 'all' : 'accuracy')}
        />
        <DimensionCard
          dimension="hallucination"
          title="Hallucination Safety"
          score={evaluation.hallucination_score * 2}
          scoreScale={10}
          description={hal?.reasoning || 'Claim-level verification of unsupported assertions and contradictions.'}
          weight={evaluation.verdict_details?.weights?.hallucination_safety ?? 0.25}
          isActive={activeTab === 'hallucination'}
          onClick={() => setActiveTab(activeTab === 'hallucination' ? 'all' : 'hallucination')}
        />
        <DimensionCard
          dimension="relevance"
          title="Prompt Relevance"
          score={evaluation.relevance_score}
          description={rel?.reasoning || 'Directness, question understanding, and topic alignment.'}
          weight={evaluation.verdict_details?.weights?.relevance ?? 0.25}
          isActive={activeTab === 'relevance'}
          onClick={() => setActiveTab(activeTab === 'relevance' ? 'all' : 'relevance')}
        />
        <DimensionCard
          dimension="completeness"
          title="Completeness"
          score={evaluation.completeness_score}
          description={comp?.reasoning || 'Coverage of all inquiry aspects, sub-questions, and depth.'}
          weight={evaluation.verdict_details?.weights?.completeness ?? 0.20}
          isActive={activeTab === 'completeness'}
          onClick={() => setActiveTab(activeTab === 'completeness' ? 'all' : 'completeness')}
        />
      </div>

      {/* 1. Accuracy Analysis (Expandable) */}
      {(activeTab === 'all' || activeTab === 'accuracy') && (
        <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
          <button
            onClick={() => toggleSection('accuracy')}
            className="w-full p-5 sm:p-6 bg-[#FAF7F2] border-b border-[#E4D7C5] flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-emerald-100 text-emerald-800 border border-emerald-300">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">1. Accuracy Analysis</h3>
                <p className="text-xs text-[#7D543E]">Evidence priority verification & factual correctness</p>
              </div>
            </div>
            {openSections.accuracy ? <ChevronUp className="w-5 h-5 text-[#7D543E]" /> : <ChevronDown className="w-5 h-5 text-[#7D543E]" />}
          </button>

          {openSections.accuracy && (
            <div className="p-6 space-y-4 text-xs">
              <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
                <span className="font-bold text-[#5C3D2E] block mb-1">Judge Reasoning:</span>
                <p className="text-[#2A1B14] leading-relaxed">{acc?.reasoning || 'No accuracy reasoning provided.'}</p>
              </div>

              {acc?.claim_assessments && acc.claim_assessments.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-[#2A1B14] uppercase tracking-wider text-[11px] block">
                    Claim-by-claim accuracy:
                  </span>
                  {acc.claim_assessments.map((item, i) => (
                    <div key={i} className="p-3 rounded-xl bg-[#FAF7F2] border border-[#E8DFC8] space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold text-[#2A1B14]">{item.claim}</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          item.status === 'correct'
                            ? 'bg-emerald-100 text-emerald-800'
                            : item.status === 'incorrect'
                            ? 'bg-rose-100 text-rose-800'
                            : item.status === 'partially_correct'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}>
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-[#5C3D2E]">{item.reasoning}</p>
                      {item.evidence && <p className="text-emerald-900"><strong>Evidence:</strong> {item.evidence}</p>}
                    </div>
                  ))}
                </div>
              )}

              {/* Supporting Evidence */}
              {acc?.supporting_evidence && acc.supporting_evidence.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-emerald-800 uppercase tracking-wider text-[11px] block">
                    Corroborated Supporting Evidence:
                  </span>
                  <div className="space-y-1.5">
                    {acc.supporting_evidence.map((ev, i) => (
                      <div key={i} className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 text-emerald-900 flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{ev}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Incorrect Claims */}
              {acc?.incorrect_claims && acc.incorrect_claims.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="font-bold text-rose-800 uppercase tracking-wider text-[11px] block">
                    Flagged Inaccuracies / Factual Discrepancies:
                  </span>
                  <div className="space-y-1.5">
                    {acc.incorrect_claims.map((ic, i) => (
                      <div key={i} className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-2">
                        <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                        <span>{ic}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 2. Hallucination Detection Analysis (Expandable & Claim-level) */}
      {(activeTab === 'all' || activeTab === 'hallucination') && (
        <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
          <button
            onClick={() => toggleSection('hallucination')}
            className="w-full p-5 sm:p-6 bg-[#FAF7F2] border-b border-[#E4D7C5] flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-rose-100 text-rose-800 border border-rose-300">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">2. Hallucination Detection (Claim-Level)</h3>
                <p className="text-xs text-[#7D543E]">
                  Status: <span className="font-bold uppercase">{hal?.hallucination_status || 'LOW'}</span> • Individual claim-by-claim breakdown
                </p>
              </div>
            </div>
            {openSections.hallucination ? <ChevronUp className="w-5 h-5 text-[#7D543E]" /> : <ChevronDown className="w-5 h-5 text-[#7D543E]" />}
          </button>

          {openSections.hallucination && (
            <div className="p-6 space-y-4 text-xs">
              <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
                <span className="font-bold text-[#5C3D2E] block mb-1">Detection Reasoning:</span>
                <p className="text-[#2A1B14] leading-relaxed">{hal?.reasoning || 'No hallucination reasoning provided.'}</p>
              </div>
              <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-between gap-4">
                <div>
                  <span className="font-bold text-rose-800 block">Hallucination Percentage</span>
                  <p className="text-rose-700 mt-1">Share of analyzed claims explicitly contradicted by available evidence. Unverified claims are not counted as confirmed hallucinations.</p>
                </div>
                <span className="text-2xl font-black text-rose-900 shrink-0">{evaluation.hallucination_percentage.toFixed(1)}%</span>
              </div>

              {/* Claim Level Table */}
              <div className="space-y-3">
                <span className="font-bold text-[#2A1B14] uppercase tracking-wider text-[11px] block">
                  Individual Factual Claims Verification:
                </span>

                {hal?.flagged_claims && hal.flagged_claims.length > 0 ? (
                  <div className="space-y-2.5">
                    {hal.flagged_claims.map((c, i) => (
                      <div key={i} className="p-4 rounded-2xl border border-[#E4D7C5] bg-[#FAF7F2] space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-bold text-[#2A1B14] text-xs">Claim #{i + 1}</span>
                          <ClaimBadge status={c.status} />
                        </div>
                        <p className="font-medium text-[#2A1B14] italic">"{c.claim}"</p>
                        <p className="text-[#5C3D2E]"><strong className="text-[#7D543E]">Reasoning:</strong> {c.reasoning}</p>
                        {c.evidence && (
                          <p className="text-emerald-900 bg-emerald-50/70 p-2 rounded-lg border border-emerald-200">
                            <strong>Corroborating Evidence:</strong> {c.evidence}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#9E775F] italic">No isolated claims flagged.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. Relevance Analysis (Expandable) */}
      {(activeTab === 'all' || activeTab === 'relevance') && (
        <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
          <button
            onClick={() => toggleSection('relevance')}
            className="w-full p-5 sm:p-6 bg-[#FAF7F2] border-b border-[#E4D7C5] flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-[#F7F3EB] text-[#8C5E3C] border border-[#E8DFC8]">
                <Target className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">3. Relevance Analysis</h3>
                <p className="text-xs text-[#7D543E]">Directness, question understanding, and topic alignment</p>
              </div>
            </div>
            {openSections.relevance ? <ChevronUp className="w-5 h-5 text-[#7D543E]" /> : <ChevronDown className="w-5 h-5 text-[#7D543E]" />}
          </button>

          {openSections.relevance && (
            <div className="p-6 space-y-4 text-xs">
              <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
                <span className="font-bold text-[#5C3D2E] block mb-1">Relevance Reasoning:</span>
                <p className="text-[#2A1B14] leading-relaxed">{rel?.reasoning || 'No relevance reasoning provided.'}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Strengths */}
                <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-200 space-y-1.5">
                  <span className="font-bold text-emerald-800 uppercase tracking-wider text-[11px] block">
                    Relevance Strengths:
                  </span>
                  {rel?.strengths && rel.strengths.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-emerald-950">
                      {rel.strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-emerald-700">None identified.</p>
                  )}
                </div>

                {/* Issues */}
                <div className="p-4 rounded-2xl bg-amber-50/50 border border-amber-200 space-y-1.5">
                  <span className="font-bold text-amber-800 uppercase tracking-wider text-[11px] block">
                    Relevance Issues:
                  </span>
                  {rel?.issues && rel.issues.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-amber-950">
                      {rel.issues.map((iss, i) => (
                        <li key={i}>{iss}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-amber-700">No relevance issues detected.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Completeness Analysis (Expandable) */}
      {(activeTab === 'all' || activeTab === 'completeness') && (
        <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
          <button
            onClick={() => toggleSection('completeness')}
            className="w-full p-5 sm:p-6 bg-[#FAF7F2] border-b border-[#E4D7C5] flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-800 border border-amber-300">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">4. Completeness Analysis</h3>
                <p className="text-xs text-[#7D543E]">Coverage of sub-questions and key requirements</p>
              </div>
            </div>
            {openSections.completeness ? <ChevronUp className="w-5 h-5 text-[#7D543E]" /> : <ChevronDown className="w-5 h-5 text-[#7D543E]" />}
          </button>

          {openSections.completeness && (
            <div className="p-6 space-y-4 text-xs">
              <div className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8]">
                <span className="font-bold text-[#5C3D2E] block mb-1">Completeness Reasoning:</span>
                <p className="text-[#2A1B14] leading-relaxed">{comp?.reasoning || 'No completeness reasoning provided.'}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Addressed */}
                <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-200 space-y-1.5">
                  <span className="font-bold text-emerald-800 uppercase tracking-wider text-[11px] block">
                    Addressed Aspects:
                  </span>
                  {comp?.addressed_aspects && comp.addressed_aspects.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-emerald-950">
                      {comp.addressed_aspects.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-emerald-700">None identified.</p>
                  )}
                </div>

                {/* Missing */}
                <div className="p-4 rounded-2xl bg-rose-50/50 border border-rose-200 space-y-1.5">
                  <span className="font-bold text-rose-800 uppercase tracking-wider text-[11px] block">
                    Missing Aspects / Omissions:
                  </span>
                  {comp?.missing_aspects && comp.missing_aspects.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1 text-rose-950">
                      {comp.missing_aspects.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-emerald-700 font-semibold">No critical aspects omitted.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. Retrieved RAG Evidence Cards */}
      {evaluation.retrieved_evidence && evaluation.retrieved_evidence.length > 0 && (
        <div className="bg-white rounded-3xl border border-[#E4D7C5] shadow-soft overflow-hidden">
          <button
            onClick={() => toggleSection('evidence')}
            className="w-full p-5 sm:p-6 bg-[#FAF7F2] border-b border-[#E4D7C5] flex items-center justify-between text-left cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-[#F7F3EB] text-[#5C3D2E] border border-[#E8DFC8]">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#2A1B14]">Retrieved RAG Evidence ({evaluation.retrieved_evidence.length})</h3>
                <p className="text-xs text-[#7D543E]">Grounding contexts retrieved from FAISS vector knowledge base</p>
              </div>
            </div>
            {openSections.evidence ? <ChevronUp className="w-5 h-5 text-[#7D543E]" /> : <ChevronDown className="w-5 h-5 text-[#7D543E]" />}
          </button>

          {openSections.evidence && (
            <div className="p-6 space-y-3 text-xs">
              {evaluation.retrieved_evidence.map((chunk, idx) => (
                <div key={idx} className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8] space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#2A1B14]">{chunk.title}</span>
                      <span className="px-2 py-0.5 rounded-full bg-[#EDE3D5] text-[#5C3D2E] text-[10px] font-bold">
                        {chunk.dataset}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold border border-emerald-300">
                      Similarity: {(chunk.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-[#3F281D] leading-relaxed italic">"{chunk.text}"</p>
                  {chunk.source && (
                    <span className="text-[10px] text-[#9E775F] block font-medium">Source: {chunk.source}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 6. Final Evaluation Summary & Recommendations */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-medium space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-[#F1ECE2]">
          <Sparkles className="w-5 h-5 text-[#8C5E3C]" />
          <h3 className="text-base font-bold text-[#2A1B14]">Final Evaluation Summary & Action Items</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Major Issues */}
          <div className="p-4 rounded-2xl bg-rose-50/50 border border-rose-200 space-y-2">
            <span className="font-bold text-rose-800 uppercase tracking-wider text-[11px] block">
              Major Issues Identified:
            </span>
            {evaluation.major_issues && evaluation.major_issues.length > 0 ? (
              <ul className="list-disc list-inside space-y-1.5 text-rose-950 font-medium">
                {evaluation.major_issues.map((iss, i) => (
                  <li key={i}>{iss}</li>
                ))}
              </ul>
            ) : (
              <p className="text-emerald-700 font-semibold">No major issues found.</p>
            )}
          </div>

          {/* Recommendations */}
          <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-200 space-y-2">
            <span className="font-bold text-emerald-800 uppercase tracking-wider text-[11px] block">
              Recommended Actions:
            </span>
            {evaluation.recommendations && evaluation.recommendations.length > 0 ? (
              <ul className="list-disc list-inside space-y-1.5 text-emerald-950 font-medium">
                {evaluation.recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            ) : (
              <p className="text-emerald-700">Ready for enterprise deployment.</p>
            )}
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-[#F1ECE2] no-print">
          <button
            onClick={onGoToHistory}
            className="text-xs font-bold text-[#5C3D2E] hover:text-[#2A1B14] cursor-pointer"
          >
            ← View All History
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] font-bold text-xs cursor-pointer shadow-2xs"
            >
              Print / Save PDF
            </button>
            <button
              onClick={onEvaluateAnother}
              className="px-5 py-2 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white font-extrabold text-xs shadow-soft cursor-pointer"
            >
              Evaluate Another Response
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
