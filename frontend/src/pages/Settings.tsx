import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Sliders,
  RotateCcw,
  Save,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Layers,
  BookOpen
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettingsConfig } from '../types/evaluation';

export const Settings: React.FC = () => {
  const [config, setConfig] = useState<SystemSettingsConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await api.getSettings();
      setConfig(data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleWeightChange = (key: keyof SystemSettingsConfig, value: number) => {
    if (!config) return;
    setConfig({ ...config, [key]: value });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;

    // Check weights sum
    const totalW = config.weight_accuracy + config.weight_hallucination + config.weight_relevance + config.weight_completeness;
    if (Math.abs(totalW - 1.0) > 0.05) {
      setMsg({
        text: `Evaluation weights must sum to 100% (Current sum: ${Math.round(totalW * 100)}%). Please adjust the sliders.`,
        type: 'error',
      });
      return;
    }

    setSaving(true);
    setMsg(null);
    try {
      const updated = await api.updateSettings(config);
      setConfig(updated);
      setMsg({ text: 'System settings updated and saved successfully.', type: 'success' });
      setTimeout(() => setMsg(null), 4000);
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to update settings', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all weights and thresholds to default certified settings?')) return;
    setSaving(true);
    setMsg(null);
    try {
      const reset = await api.resetSettings();
      setConfig(reset);
      setMsg({ text: 'Settings successfully restored to defaults.', type: 'success' });
      setTimeout(() => setMsg(null), 4000);
    } catch (err: any) {
      setMsg({ text: err.message || 'Failed to reset settings', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (!config) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-xs text-[#9E775F]">
        Loading system configuration...
      </div>
    );
  }

  const weightSum = Math.round(
    (config.weight_accuracy + config.weight_hallucination + config.weight_relevance + config.weight_completeness) * 100
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            System & Evaluation Settings
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Tune multi-agent scoring weights, verdict thresholds, and vector retrieval hyper-parameters.
          </p>
        </div>

        <button
          onClick={handleReset}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset to Defaults
        </button>
      </div>

      {msg && (
        <div
          className={`p-4 rounded-2xl border flex items-center gap-2.5 text-xs font-semibold ${
            msg.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {msg.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{msg.text}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* 1. Evaluation Dimension Weights */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-soft space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-4 border-b border-[#F1ECE2]">
            <div className="flex items-center gap-2.5">
              <Sliders className="w-5 h-5 text-[#8C5E3C]" />
              <h3 className="text-base font-bold text-[#2A1B14]">
                Evaluation Dimension Weights (Must Sum to 100%)
              </h3>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-black border ${
                weightSum === 100
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : 'bg-rose-100 text-rose-800 border-rose-300'
              }`}
            >
              Current Sum: {weightSum}%
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            {/* Accuracy Weight */}
            <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#2A1B14]">Accuracy Weight:</span>
                <span className="font-mono font-black text-sm text-[#2A1B14]">
                  {Math.round(config.weight_accuracy * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.weight_accuracy}
                onChange={(e) => handleWeightChange('weight_accuracy', parseFloat(e.target.value))}
                className="w-full accent-emerald-600"
              />
              <span className="text-[10px] text-[#9E775F] block">Default: 35%</span>
            </div>

            {/* Hallucination Safety Weight */}
            <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#2A1B14]">Hallucination Safety Weight:</span>
                <span className="font-mono font-black text-sm text-[#2A1B14]">
                  {Math.round(config.weight_hallucination * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.weight_hallucination}
                onChange={(e) => handleWeightChange('weight_hallucination', parseFloat(e.target.value))}
                className="w-full accent-rose-600"
              />
              <span className="text-[10px] text-[#9E775F] block">Default: 25%</span>
            </div>

            {/* Relevance Weight */}
            <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#2A1B14]">Relevance Weight:</span>
                <span className="font-mono font-black text-sm text-[#2A1B14]">
                  {Math.round(config.weight_relevance * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.weight_relevance}
                onChange={(e) => handleWeightChange('weight_relevance', parseFloat(e.target.value))}
                className="w-full accent-[#8C5E3C]"
              />
              <span className="text-[10px] text-[#9E775F] block">Default: 25%</span>
            </div>

            {/* Completeness Weight */}
            <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#2A1B14]">Completeness Weight:</span>
                <span className="font-mono font-black text-sm text-[#2A1B14]">
                  {Math.round(config.weight_completeness * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.weight_completeness}
                onChange={(e) => handleWeightChange('weight_completeness', parseFloat(e.target.value))}
                className="w-full accent-amber-600"
              />
              <span className="text-[10px] text-[#9E775F] block">Default: 15%</span>
            </div>
          </div>
        </div>

        {/* 2. Verdict Thresholds */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-soft space-y-6">
          <div className="pb-4 border-b border-[#F1ECE2]">
            <h3 className="text-base font-bold text-[#2A1B14]">Verdict Score Thresholds</h3>
            <p className="text-xs text-[#7D543E]">Define the score boundaries that separate PASS, NEEDS IMPROVEMENT, and FAIL.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
            <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-200 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-emerald-950">Pass Threshold (&gt;= Score):</span>
                <span className="font-mono font-black text-sm text-emerald-800">{config.threshold_pass}</span>
              </div>
              <input
                type="range"
                min="50"
                max="95"
                step="1"
                value={config.threshold_pass}
                onChange={(e) => setConfig({ ...config, threshold_pass: parseFloat(e.target.value) })}
                className="w-full accent-emerald-600"
              />
              <span className="text-[10px] text-emerald-700 block">Default: 75.0 points</span>
            </div>

            <div className="p-4 rounded-2xl bg-amber-50/50 border border-amber-200 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-amber-950">Needs Improvement Threshold (&gt;= Score):</span>
                <span className="font-mono font-black text-sm text-amber-800">{config.threshold_needs_improvement}</span>
              </div>
              <input
                type="range"
                min="30"
                max="70"
                step="1"
                value={config.threshold_needs_improvement}
                onChange={(e) => setConfig({ ...config, threshold_needs_improvement: parseFloat(e.target.value) })}
                className="w-full accent-amber-600"
              />
              <span className="text-[10px] text-amber-700 block">Default: 50.0 points</span>
            </div>
          </div>
        </div>

        {/* 3. Vector Retrieval & LLM Settings */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E4D7C5] shadow-soft space-y-6">
          <div className="pb-4 border-b border-[#F1ECE2]">
            <h3 className="text-base font-bold text-[#2A1B14]">RAG Vector & LLM Hyperparameters</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Retrieval Top-K Chunks</label>
              <input
                type="number"
                min="1"
                max="10"
                value={config.retrieval_top_k}
                onChange={(e) => setConfig({ ...config, retrieval_top_k: parseInt(e.target.value) || 4 })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              />
            </div>

            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Text Chunk Size (chars)</label>
              <input
                type="number"
                min="100"
                max="1000"
                step="50"
                value={config.chunk_size}
                onChange={(e) => setConfig({ ...config, chunk_size: parseInt(e.target.value) || 300 })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              />
            </div>

            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Chunk Overlap (chars)</label>
              <input
                type="number"
                min="10"
                max="200"
                step="10"
                value={config.chunk_overlap}
                onChange={(e) => setConfig({ ...config, chunk_overlap: parseInt(e.target.value) || 50 })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              />
            </div>

            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">LLM Provider</label>
              <select
                value={config.llm_provider}
                onChange={(e) => setConfig({ ...config, llm_provider: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              >
                <option value="local">Local Intelligent Rule & Semantic Analyzer (Default)</option>
                <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
                <option value="gemini">Google Gemini (Gemini 1.5 Flash)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Hallucination Sensitivity</label>
              <select
                value={config.hallucination_sensitivity}
                onChange={(e) => setConfig({ ...config, hallucination_sensitivity: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              >
                <option value="low">Low (Permissive)</option>
                <option value="standard">Standard (Recommended)</option>
                <option value="high">High (Strict Entailment)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Temperature</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) || 0.2 })}
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] font-bold"
              />
            </div>
          </div>
        </div>

        {/* Save button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-8 py-3 rounded-2xl bg-gradient-to-r from-[#5C3D2E] to-[#3F281D] hover:from-[#4A3024] hover:to-[#2A1B14] text-white text-xs font-black shadow-medium transition-all transform active:scale-95 flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving Settings...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
};
