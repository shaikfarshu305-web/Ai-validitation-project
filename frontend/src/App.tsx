import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopNavbar } from './components/TopNavbar';

import { Dashboard } from './pages/Dashboard';
import { VerifyResponse } from './pages/VerifyResponse';
import { EvaluationDetailView } from './pages/EvaluationDetailView';
import { BatchVerify } from './pages/BatchVerify';
import { EvidenceLibrary } from './pages/EvidenceLibrary';
import { EvaluationHistory } from './pages/EvaluationHistory';
import { Reports } from './pages/Reports';
import { VerificationInsights } from './pages/VerificationInsights';
import { SystemStatus } from './pages/SystemStatus';
import { Settings } from './pages/Settings';

import { EvaluationDetail } from './types/evaluation';
import { api } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Active evaluation for detail view
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // System status pill data
  const [systemOnline, setSystemOnline] = useState('ONLINE');
  const [currentModel, setCurrentModel] = useState('Local NLP & Semantic Analyzer');

  useEffect(() => {
    api.getSystemStatus().then((res) => {
      setSystemOnline(res.overall_status || 'ONLINE');
      setCurrentModel(res.current_model || 'Local NLP & Semantic Analyzer');
    }).catch(() => {
      // Offline fallback
    });
  }, []);

  const handleViewEvaluation = async (evalId: string) => {
    setLoadingDetail(true);
    try {
      const data = await api.getEvaluationDetail(evalId);
      setSelectedEvaluation(data);
      setCurrentTab('detail');
    } catch (err: any) {
      alert(err.message || 'Failed to load evaluation detail');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleEvaluationComplete = (result: EvaluationDetail) => {
    setSelectedEvaluation(result);
    setCurrentTab('detail');
  };

  const getPageInfo = () => {
    switch (currentTab) {
      case 'dashboard':
        return { title: 'Analytics Dashboard', subtitle: 'Overview of AI verification metrics, benchmarks, and verdicts' };
      case 'verify':
        return { title: 'Verify AI Response', subtitle: 'Interactive 4-dimension grounded verification' };
      case 'batch':
        return { title: 'Batch Verification', subtitle: 'Bulk CSV dataset evaluation and export' };
      case 'history':
        return { title: 'Evaluation History', subtitle: 'Historical audit log and dimensional queries' };
      case 'evidence':
        return { title: 'Evidence Library', subtitle: 'Vector knowledge base and semantic search test bench' };
      case 'insights':
        return { title: 'Verification Insights', subtitle: 'Quality trends and hallucination reduction analytics' };
      case 'reports':
        return { title: 'Audit Reports', subtitle: 'Generate and print compliance-ready verification reports' };
      case 'system':
        return { title: 'System Status', subtitle: 'Live diagnostic telemetry across components' };
      case 'settings':
        return { title: 'System Settings', subtitle: 'Configurable weights, thresholds, and hyper-parameters' };
      case 'detail':
        return { title: 'Evaluation Detail', subtitle: 'Deep dive multi-agent audit breakdown' };
      default:
        return { title: 'AI Response Validation System', subtitle: 'AI evaluation and validation workspace' };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <div className="min-h-screen bg-[#F7F3EB] text-[#2A1B14] flex">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          if (tab !== 'detail') setSelectedEvaluation(null);
        }}
        isOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0">
        {/* Sticky Top Navbar */}
        <TopNavbar
          pageTitle={pageInfo.title}
          pageSubtitle={pageInfo.subtitle}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          onNewVerify={() => {
            setCurrentTab('verify');
            setSelectedEvaluation(null);
          }}
          systemStatus={systemOnline}
          currentModel={currentModel}
        />

        {/* Page Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {loadingDetail && (
            <div className="text-center py-16 text-xs text-[#7D543E]">
              Loading evaluation audit report...
            </div>
          )}

          {!loadingDetail && currentTab === 'dashboard' && (
            <Dashboard
              onViewEvaluation={handleViewEvaluation}
              onNavigateToVerify={() => setCurrentTab('verify')}
            />
          )}

          {!loadingDetail && currentTab === 'verify' && (
            <VerifyResponse onEvaluationComplete={handleEvaluationComplete} />
          )}

          {!loadingDetail && currentTab === 'detail' && selectedEvaluation && (
            <EvaluationDetailView
              evaluation={selectedEvaluation}
              onBack={() => setCurrentTab('dashboard')}
              onEvaluateAnother={() => {
                setSelectedEvaluation(null);
                setCurrentTab('verify');
              }}
              onGoToHistory={() => setCurrentTab('history')}
            />
          )}

          {!loadingDetail && currentTab === 'batch' && (
            <BatchVerify onViewEvaluation={handleViewEvaluation} />
          )}

          {!loadingDetail && currentTab === 'history' && (
            <EvaluationHistory onViewEvaluation={handleViewEvaluation} />
          )}

          {!loadingDetail && currentTab === 'evidence' && (
            <EvidenceLibrary />
          )}

          {!loadingDetail && currentTab === 'insights' && (
            <VerificationInsights />
          )}

          {!loadingDetail && currentTab === 'reports' && (
            <Reports />
          )}

          {!loadingDetail && currentTab === 'system' && (
            <SystemStatus />
          )}

          {!loadingDetail && currentTab === 'settings' && (
            <Settings />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
