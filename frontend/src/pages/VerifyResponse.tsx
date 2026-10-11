import React, { useState } from 'react';
import {
  Send,
  Trash2,
  Sparkles,
  BookOpen,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Layers,
  ShieldAlert,
  Target,
  Gavel
} from 'lucide-react';
import { api } from '../services/api';
import { EvaluationDetail } from '../types/evaluation';

interface Props {
  onEvaluationComplete: (result: EvaluationDetail) => void;
}

const PRESET_EXAMPLES = [
  {
    name: 'Astronomy (High Quality - PASS)',
    question: 'Why does Earth experience different seasons throughout the year?',
    ai_response: 'Earth experiences seasons primarily due to its 23.5-degree axial tilt as it orbits the Sun. When the Northern Hemisphere is tilted towards the Sun, it receives direct sunlight and longer daylight hours, causing summer, while the Southern Hemisphere experiences winter.',
    reference_answer: "Earth's seasons are caused by its 23.5° axial tilt, which alters solar incidence and daylight duration.",
    source_information: 'Planetary Astronomy Reference Manual'
  },
  {
    name: 'Myth & Hallucination (FAIL)',
    question: 'Is the Great Wall of China visible to astronauts from space with the naked eye?',
    ai_response: 'Yes, the Great Wall of China is famously the only man-made structure visible from space and the Moon without telescopes. Astronauts can easily see its distinct continuous outline spanning across mountain ridges from Earth orbit.',
    reference_answer: 'The Great Wall is NOT visible from space or the Moon with the unaided human eye; this is a widely debunked myth.',
    source_information: 'NASA Astronaut Debriefs & ESA Satellite Records'
  },
  {
    name: 'Incomplete Response (NEEDS IMPROVEMENT)',
    question: 'How do mRNA vaccines work, and how long does the mRNA stay in the human body?',
    ai_response: 'mRNA vaccines work by delivering instructions to host cells to make a viral protein, like the coronavirus spike protein. This causes your immune system to produce protective antibodies and activate T-cells.',
    reference_answer: 'mRNA vaccines instruct cells via LNPs to produce the viral spike protein. The synthetic mRNA degrades naturally within a few days.',
    source_information: 'Medical Immunology Text'
  }
];

const EVAL_STEPS = [
  { id: 1, label: 'Preparing Input & Normalizing Text', icon: <FileText className="w-4 h-4" /> },
  { id: 2, label: 'Retrieving Knowledge Base Evidence (RAG)', icon: <BookOpen className="w-4 h-4" /> },
  { id: 3, label: 'Running Relevance Judge Agent', icon: <Target className="w-4 h-4" /> },
  { id: 4, label: 'Running Accuracy Judge Agent', icon: <CheckCircle2 className="w-4 h-4" /> },
  { id: 5, label: 'Detecting Claim-Level Hallucinations', icon: <ShieldAlert className="w-4 h-4" /> },
  { id: 6, label: 'Checking Information Completeness', icon: <Layers className="w-4 h-4" /> },
  { id: 7, label: 'Synthesizing Final Verdict & Scores', icon: <Gavel className="w-4 h-4" /> },
];

export const VerifyResponse: React.FC<Props> = ({ onEvaluationComplete }) => {
  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [sourceInformation, setSourceInformation] = useState('');

  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const handleClear = () => {
    setQuestion('');
    setAiResponse('');
    setReferenceAnswer('');
    setSourceInformation('');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError('Please provide a Question to evaluate.');
      return;
    }
    if (!aiResponse.trim()) {
      setError('Please provide the AI Response to verify.');
      return;
    }

    setLoading(true);
    setError(null);
    setCurrentStep(1);

    // Simulate multi-stage visual pipeline progression while API runs
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < 7 ? prev + 1 : prev));
    }, 450);

    try {
      const result = await api.evaluateResponse({
        question: question.trim(),
        ai_response: aiResponse.trim(),
        reference_answer: referenceAnswer.trim() || undefined,
        source_information: sourceInformation.trim() || undefined,
      });

      clearInterval(stepInterval);
      setCurrentStep(7);
      setTimeout(() => {
        setLoading(false);
        onEvaluationComplete(result);
      }, 400);
    } catch (err: any) {
      clearInterval(stepInterval);
      setLoading(false);
      setError(err.message || 'Verification pipeline encountered an unexpected error.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Verify AI Response
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Submit prompts and AI outputs for 4-dimension RAG-grounded multi-agent verification.
          </p>
        </div>
      </div>

      {/* Progress State Overlay when executing */}
      {loading ? (
        <div className="bg-white rounded-3xl p-8 border border-[#E4D7C5] shadow-medium text-center space-y-6 animate-fade-in">
          <div className="inline-flex p-4 rounded-2xl bg-[#F7F3EB] text-[#5C3D2E] mb-2 animate-bounce">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
          <div>
            <h3 className="text-lg font-black text-[#2A1B14]">
              Multi-Agent Verification In Progress
            </h3>
            <p className="text-xs text-[#7D543E]">
              AI validation orchestrator is executing evidence retrieval and independent judge agents...
            </p>
          </div>

          {/* Stepper Pipeline */}
          <div className="max-w-md mx-auto space-y-2 text-left">
            {EVAL_STEPS.map((step) => {
              const isPast = currentStep > step.id;
              const isCurrent = currentStep === step.id;
              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 p-2.5 rounded-xl border text-xs transition-all ${
                    isPast
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : isCurrent
                      ? 'bg-[#F7F3EB] border-[#7D543E] text-[#2A1B14] font-bold shadow-xs'
                      : 'bg-white border-[#F1ECE2] text-[#9E775F] opacity-60'
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
                      isPast
                        ? 'bg-emerald-600 text-white'
                        : isCurrent
                        ? 'bg-[#7D543E] text-white animate-pulse'
                        : 'bg-[#F1ECE2] text-[#9E775F]'
                    }`}
                  >
                    {isPast ? <CheckCircle2 className="w-3.5 h-3.5" /> : step.id}
                  </div>
                  <span className="flex-1">{step.label}</span>
                  {isCurrent && <Loader2 className="w-3.5 h-3.5 animate-spin text-[#7D543E]" />}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Evaluation Input Form */
        <form onSubmit={handleSubmit} className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-soft space-y-6">
          {error && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-3 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Question Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-[#2A1B14] uppercase tracking-wider">
                Question / Prompt <span className="text-rose-600">*</span>
              </label>
              <span className="text-[11px] text-[#9E775F]">{question.length} characters</span>
            </div>
            <textarea
              required
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Why does Earth experience different seasons throughout the year?"
              className="w-full p-3.5 rounded-2xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] text-xs sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30 focus:border-[#7D543E] transition-all"
            />
          </div>

          {/* AI Response Input */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-[#2A1B14] uppercase tracking-wider">
                AI Response to Verify <span className="text-rose-600">*</span>
              </label>
              <span className="text-[11px] text-[#9E775F]">{aiResponse.length} characters</span>
            </div>
            <textarea
              required
              rows={5}
              value={aiResponse}
              onChange={(e) => setAiResponse(e.target.value)}
              placeholder="Paste the generated response from your LLM model here..."
              className="w-full p-3.5 rounded-2xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] text-xs sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30 focus:border-[#7D543E] transition-all"
            />
          </div>

          {/* Optional Ground Truth Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-[#F1ECE2]">
            {/* Reference Answer */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-[#5C3D2E]">
                  Reference Answer <span className="text-[10px] text-[#9E775F]">(Optional)</span>
                </label>
              </div>
              <textarea
                rows={3}
                value={referenceAnswer}
                onChange={(e) => setReferenceAnswer(e.target.value)}
                placeholder="Ground truth reference answer (if available)..."
                className="w-full p-3 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] text-xs focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30 transition-all"
              />
            </div>

            {/* Source Information */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-[#5C3D2E]">
                  Source Document / Context <span className="text-[10px] text-[#9E775F]">(Optional)</span>
                </label>
              </div>
              <textarea
                rows={3}
                value={sourceInformation}
                onChange={(e) => setSourceInformation(e.target.value)}
                placeholder="Paste reference text or citations from source documents..."
                className="w-full p-3 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] text-xs focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30 transition-all"
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#F1ECE2]">
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 rounded-xl border border-[#E4D7C5] text-[#5C3D2E] hover:bg-[#F7F3EB] font-bold text-xs transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#5C3D2E] to-[#3F281D] hover:from-[#4A3024] hover:to-[#2A1B14] text-white font-extrabold text-xs shadow-soft transition-all transform active:scale-95 flex items-center gap-2 cursor-pointer"
            >
              <Send className="w-4 h-4" />
              Evaluate Response
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
