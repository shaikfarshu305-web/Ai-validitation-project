import React, { useState, useEffect } from 'react';
import {
  Library,
  Search,
  BookOpen,
  PlusCircle,
  Database,
  Cpu,
  Layers,
  Sparkles,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { api } from '../services/api';
import { RetrievedChunk } from '../types/evaluation';

export const EvidenceLibrary: React.FC = () => {
  const [stats, setStats] = useState<{
    total_documents: number;
    total_chunks: number;
    total_embeddings: number;
    datasets: string[];
  } | null>(null);

  const [loadingStats, setLoadingStats] = useState(true);

  // Search state
  const [searchQuery, setSearchQuery] = useState('Why does Earth have seasons?');
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [topK, setTopK] = useState(4);
  const [searchResults, setSearchResults] = useState<RetrievedChunk[]>([]);
  const [searching, setSearching] = useState(false);

  // Ingestion form state
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [ingestTitle, setIngestTitle] = useState('');
  const [ingestDataset, setIngestDataset] = useState('Custom');
  const [ingestContent, setIngestContent] = useState('');
  const [ingestSource, setIngestSource] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);

  const loadStats = async () => {
    setLoadingStats(true);
    try {
      const data = await api.getKnowledgeStats();
      setStats(data);
    } catch {
      // fallback
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    loadStats();
    handleSearch('Earth orbital tilt and seasons', 4);
  }, []);

  const handleSearch = async (queryToSearch = searchQuery, k = topK) => {
    if (!queryToSearch.trim()) return;
    setSearching(true);
    try {
      const res = await api.searchKnowledgeBase(queryToSearch, k, selectedDataset || undefined);
      setSearchResults(res.results || []);
    } catch {
      // fallback
    } finally {
      setSearching(false);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestTitle.trim() || !ingestContent.trim()) return;
    setIngesting(true);
    setIngestSuccess(null);
    try {
      const res = await api.ingestDocument({
        dataset: ingestDataset,
        title: ingestTitle,
        content: ingestContent,
        source: ingestSource || undefined,
      });
      setIngestSuccess(`Ingested successfully (${res.chunks_indexed} chunks created).`);
      setIngestTitle('');
      setIngestContent('');
      setIngestSource('');
      loadStats();
      setTimeout(() => setIngestSuccess(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Ingestion failed');
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-[#2A1B14] tracking-tight">
            Evidence Library
          </h2>
          <p className="text-xs sm:text-sm text-[#7D543E]">
            Inspect indexed knowledge chunks, test vector similarity retrieval, and ingest evidence.
          </p>
        </div>

        <button
          onClick={() => setShowIngestModal(!showIngestModal)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-bold shadow-soft transition-all self-start sm:self-auto cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          {showIngestModal ? 'Close Ingestion Form' : 'Ingest New Document'}
        </button>
      </div>

      {/* 4 Knowledge Base Statistic Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <div className="flex items-center justify-between text-[#7D543E] mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Documents</span>
            <BookOpen className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{stats?.total_documents ?? 0}</span>
          <span className="text-[10px] text-[#9E775F] block mt-1">Grounding reference texts</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <div className="flex items-center justify-between text-[#7D543E] mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Chunks</span>
            <Layers className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{stats?.total_chunks ?? 0}</span>
          <span className="text-[10px] text-[#9E775F] block mt-1">Overlapping text chunks</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <div className="flex items-center justify-between text-[#7D543E] mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Vectors</span>
            <Cpu className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <span className="text-2xl font-black text-[#2A1B14]">{stats?.total_embeddings ?? 0}</span>
          <span className="text-[10px] text-[#9E775F] block mt-1">128-dim FAISS vectors</span>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-[#E4D7C5] shadow-xs">
          <div className="flex items-center justify-between text-[#7D543E] mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider">Benchmark Sets</span>
            <Database className="w-4 h-4 text-[#8C5E3C]" />
          </div>
          <div className="flex flex-wrap gap-1 mt-1">
            {(stats?.datasets || ['TruthfulQA', 'SQuAD']).map((d) => (
              <span key={d} className="px-2 py-0.5 rounded-full bg-[#FAF7F2] text-[#5C3D2E] text-[10px] font-bold border border-[#E4D7C5]">
                {d}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Ingest Document Drawer / Card */}
      {showIngestModal && (
        <form onSubmit={handleIngest} className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-medium space-y-4 animate-fade-in">
          <div className="flex items-center justify-between pb-3 border-b border-[#F1ECE2]">
            <div className="flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-[#8C5E3C]" />
              <h3 className="text-sm font-bold text-[#2A1B14]">Ingest Document Into RAG Vector Database</h3>
            </div>
            {ingestSuccess && (
              <span className="text-xs text-emerald-700 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {ingestSuccess}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Document Title *</label>
              <input
                type="text"
                required
                value={ingestTitle}
                onChange={(e) => setIngestTitle(e.target.value)}
                placeholder="e.g. Atmospheric Chemistry Reference"
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14]"
              />
            </div>
            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Dataset / Collection</label>
              <input
                type="text"
                value={ingestDataset}
                onChange={(e) => setIngestDataset(e.target.value)}
                placeholder="e.g. Custom, TruthfulQA, SQuAD"
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14]"
              />
            </div>
            <div>
              <label className="font-semibold text-[#5C3D2E] block mb-1">Source / Citation</label>
              <input
                type="text"
                value={ingestSource}
                onChange={(e) => setIngestSource(e.target.value)}
                placeholder="e.g. NASA Goddard Earth Data"
                className="w-full p-2.5 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14]"
              />
            </div>
          </div>

          <div className="text-xs">
            <label className="font-semibold text-[#5C3D2E] block mb-1">Document Content *</label>
            <textarea
              required
              rows={4}
              value={ingestContent}
              onChange={(e) => setIngestContent(e.target.value)}
              placeholder="Paste complete ground truth article, research summary, or verification corpus here..."
              className="w-full p-3 rounded-xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowIngestModal(false)}
              className="px-4 py-1.5 rounded-xl border border-[#E4D7C5] text-xs font-bold text-[#5C3D2E]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={ingesting}
              className="px-5 py-1.5 rounded-xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-bold shadow-soft flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              {ingesting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              {ingesting ? 'Chunking & Embedding...' : 'Clean, Chunk & Index'}
            </button>
          </div>
        </form>
      )}

      {/* Semantic Search Testing Interface */}
      <div className="bg-white rounded-3xl p-6 border border-[#E4D7C5] shadow-soft space-y-5">
        <div>
          <h3 className="text-base font-bold text-[#2A1B14]">
            Semantic Vector Retrieval Test Bench
          </h3>
          <p className="text-xs text-[#7D543E]">
            Test query matching against the FAISS vector index with cosine similarity scores.
          </p>
        </div>

        {/* Search controls */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#9E775F] absolute left-3.5 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter test retrieval query (e.g. 'Can humans breathe underwater?')..."
              className="w-full pl-10 pr-4 py-2.5 rounded-2xl border border-[#E4D7C5] bg-[#FAF7F2] text-[#2A1B14] text-xs sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-[#7D543E]/30"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="px-3 py-2.5 rounded-2xl border border-[#E4D7C5] bg-[#FAF7F2] text-xs font-semibold text-[#5C3D2E]"
            >
              <option value={2}>Top 2</option>
              <option value={4}>Top 4</option>
              <option value={6}>Top 6</option>
            </select>

            <button
              onClick={() => handleSearch()}
              disabled={searching}
              className="px-5 py-2.5 rounded-2xl bg-[#5C3D2E] hover:bg-[#3F281D] text-white text-xs font-bold shadow-soft transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shrink-0"
            >
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {searching ? 'Retrieving...' : 'Search Vector DB'}
            </button>
          </div>
        </div>

        {/* Results List */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between text-xs text-[#7D543E]">
            <span className="font-bold">Retrieved Evidence Chunks ({searchResults.length}):</span>
            <span>Sorted by Cosine Similarity</span>
          </div>

          {searchResults.length === 0 ? (
            <div className="p-8 text-center bg-[#FAF7F2] rounded-2xl border border-[#E8DFC8] text-xs text-[#9E775F]">
              No matching chunks found above threshold. Try broader keywords or ingest relevant articles.
            </div>
          ) : (
            <div className="space-y-3">
              {searchResults.map((res, i) => (
                <div key={i} className="p-4 rounded-2xl bg-[#FCFAF6] border border-[#E8DFC8] space-y-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#2A1B14] text-sm">{res.title}</span>
                      <span className="px-2 py-0.5 rounded-full bg-[#EDE3D5] text-[#5C3D2E] text-[10px] font-bold">
                        {res.dataset}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold border border-emerald-300">
                      Similarity: {(res.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>

                  <p className="text-[#3F281D] leading-relaxed italic bg-white p-3 rounded-xl border border-[#F1ECE2]">
                    "{res.text}"
                  </p>

                  <div className="flex flex-wrap items-center justify-between text-[11px] text-[#9E775F] pt-1">
                    <span>Source: {res.source || 'Knowledge Corpus'}</span>
                    <span className="font-mono text-[10px]">ID: {res.chunk_id.slice(0, 16)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
