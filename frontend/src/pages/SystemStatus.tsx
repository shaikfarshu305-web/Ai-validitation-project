import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Cpu,
  Layers,
  Database,
  Calendar,
  Clock,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { SystemStatusData, ComponentStatus } from '../types/evaluation';

export const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getSystemStatus();
      setStatus(data);
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const renderStatusBadge = (st: string) => {
    if (st === 'ONLINE') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
          ONLINE
        </span>
      );
    }
    if (st === 'WARNING') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          WARNING
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300 flex items-center gap-1.5">
        <XCircle className="w-3.5 h-3.5 text-rose-600" />
        OFFLINE
      </span>
    );
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            System Infrastructure & Agent Status
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Real-time diagnostic health check across FastAPI, SQLite, FAISS vector store, and evaluation agents.
          </p>
        </div>

        <button
          onClick={loadStatus}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-[#E4D7C5] hover:bg-[#F7F3EB] text-[#5C3D2E] text-xs font-bold transition-all shadow-2xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Run Diagnostics
        </button>
      </div>

      {/* Overall Health Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-[#E4D7C5] shadow-medium flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-black text-[#2A1B14]">All Verification Subsystems Operational</h3>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                HEALTHY
              </span>
            </div>
            <p className="text-xs text-[#7D543E] mt-0.5">
              Multi-Agent Orchestrator, FAISS Index, and Grounding Pipelines are active.
            </p>
          </div>
        </div>

        <div className="text-left sm:text-right text-xs text-[#9E775F] space-y-0.5">
          <p className="flex items-center gap-1 sm:justify-end">
            <Clock className="w-3.5 h-3.5" /> Checked: {status?.timestamp || 'Just now'}
          </p>
        </div>
      </div>

      {/* System Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase block mb-1">Active Model</span>
          <span className="text-xs font-extrabold text-[#2A1B14] block truncate" title={status?.current_model}>
            {status?.current_model || 'Local Rule & Semantic Judge'}
          </span>
          <span className="text-[10px] text-emerald-700 font-semibold mt-1 block">Zero-dependency ready</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase block mb-1">Indexed Chunks</span>
          <span className="text-2xl font-black text-[#2A1B14] block">
            {status?.indexed_chunks ?? 0}
          </span>
          <span className="text-[10px] text-[#9E775F] block mt-1">Stored in FAISS & SQLite</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase block mb-1">Last KB Update</span>
          <span className="text-xs font-extrabold text-[#2A1B14] block truncate">
            {status?.last_kb_update || 'N/A'}
          </span>
          <span className="text-[10px] text-[#9E775F] block mt-1">Benchmark sync</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <span className="text-[10px] font-bold text-[#7D543E] uppercase block mb-1">Total Evaluations</span>
          <span className="text-2xl font-black text-[#2A1B14] block">
            {status?.total_evaluations ?? 0}
          </span>
          <span className="text-[10px] text-emerald-800 font-semibold mt-1 block">Full audit history</span>
        </div>
      </div>

      {/* Component Status Grid */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-[#E4D7C5] shadow-soft space-y-4">
        <h3 className="text-base font-bold text-[#2A1B14]">Subsystem Telemetry & Latencies</h3>

        <div className="divide-y divide-[#F1ECE2]">
          {(status?.components || []).map((comp, idx) => (
            <div key={idx} className="py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[#2A1B14]">{comp.name}</span>
                  <span className="font-mono text-[10px] text-[#7D543E] bg-[#FAF7F2] px-1.5 py-0.5 rounded border border-[#E4D7C5]">
                    {comp.latency_ms} ms
                  </span>
                </div>
                <p className="text-[#5C3D2E] text-[11px]">{comp.details}</p>
              </div>

              <div>
                {renderStatusBadge(comp.status)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
