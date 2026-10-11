import React, { useState, useEffect } from 'react';
import {
  Database,
  RefreshCw,
  RotateCw,
  ExternalLink,
  CheckCircle2,
  Cpu,
  Layers,
  Calendar,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';
import { DataSourceItem } from '../types/evaluation';

export const DataSources: React.FC = () => {
  const [sources, setSources] = useState<DataSourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const loadSources = async () => {
    setLoading(true);
    try {
      const data = await api.getDataSources();
      setSources(data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleReindex = async (name: string) => {
    setReindexing(name);
    setMsg(null);
    try {
      const res = await api.reindexDataSource(name);
      setMsg(`Reindexed ${name} successfully (${res.reindexed_documents} documents processed).`);
      loadSources();
      setTimeout(() => setMsg(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Reindex failed');
    } finally {
      setReindexing(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Data Sources & Benchmark Corpora
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Grounding datasets supporting evidence retrieval for TruthfulQA and SQuAD benchmarks.
          </p>
        </div>

        <button
          onClick={loadSources}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {msg && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-2 text-xs font-semibold animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{msg}</span>
        </div>
      )}

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {sources.map((src) => (
          <div
            key={src.name}
            className="bg-white rounded-3xl p-6 sm:p-7 border border-[#E4D7C5] shadow-soft flex flex-col justify-between space-y-6"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-[#F7F3EB] border border-[#E8DFC8] text-[#5C3D2E]">
                    <Database className="w-5 h-5 text-[#8C5E3C]" />
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold text-[#2A1B14]">{src.name}</h3>
                    <span className="text-[11px] font-semibold text-[#7D543E]">Benchmark Collection</span>
                  </div>
                </div>

                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  {src.status}
                </span>
              </div>

              <p className="text-xs text-[#5C3D2E] leading-relaxed mb-4">
                {src.description}
              </p>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-3 p-3.5 rounded-2xl bg-[#FAF7F2] border border-[#E8DFC8] text-center text-xs">
                <div>
                  <span className="text-[10px] font-bold text-[#7D543E] uppercase block">Documents</span>
                  <span className="text-base font-black text-[#2A1B14] mt-0.5 block">{src.num_records}</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-[#7D543E] uppercase block">Index Status</span>
                  <span className="text-base font-black text-emerald-700 mt-0.5 block">{src.vector_index_status}</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-[#7D543E] uppercase block">Vector Store</span>
                  <span className="text-base font-black text-[#8C5E3C] mt-0.5 block">FAISS</span>
                </div>
              </div>
            </div>

            {/* Bottom Actions & Last Indexed */}
            <div className="pt-4 border-t border-[#F1ECE2] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
              <span className="text-[11px] text-[#9E775F] flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> Last Indexed: {src.last_indexed}
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReindex(src.name)}
                  disabled={reindexing === src.name}
                  className="px-3.5 py-1.5 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] font-bold text-xs transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${reindexing === src.name ? 'animate-spin' : ''}`} />
                  {reindexing === src.name ? 'Reindexing...' : 'Reindex'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
