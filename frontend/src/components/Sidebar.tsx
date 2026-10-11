import React from 'react';
import {
  CheckCircle2,
  FileSpreadsheet,
  History,
  Library,
  BarChart3,
  FileText,
  Activity,
  Settings,
  LayoutDashboard,
  X
} from 'lucide-react';

interface Props {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<Props> = ({
  currentTab,
  onSelectTab,
  isOpen,
  onCloseMobile,
}) => {
  const navSections = [
    {
      title: 'OVERVIEW',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
      ],
    },
    {
      title: 'VERIFY',
      items: [
        { id: 'verify', label: 'Verify Response', icon: <CheckCircle2 className="w-4 h-4" /> },
        { id: 'batch', label: 'Batch Verify', icon: <FileSpreadsheet className="w-4 h-4" /> },
        { id: 'history', label: 'Evaluation History', icon: <History className="w-4 h-4" /> },
      ],
    },
    {
      title: 'EVIDENCE',
      items: [
        { id: 'evidence', label: 'Evidence Library', icon: <Library className="w-4 h-4" /> },
      ],
    },
    {
      title: 'INSIGHTS',
      items: [
        { id: 'insights', label: 'Verification Insights', icon: <BarChart3 className="w-4 h-4" /> },
        { id: 'reports', label: 'Reports', icon: <FileText className="w-4 h-4" /> },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'system', label: 'System Status', icon: <Activity className="w-4 h-4" /> },
        { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
      ],
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-[#180E0A]/40 z-40 lg:hidden backdrop-blur-xs"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#2A1B14] text-[#F7F3EB] flex flex-col justify-between border-r border-[#3F281D] transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Header / Branding */}
        <div>
          <div className="p-5 border-b border-[#3F281D] flex items-center justify-between">
            <div className="flex-1">
              <h1 className="font-bold text-[15px] leading-tight text-white tracking-tight">
                AI Response Validation System
              </h1>
              <p className="text-[10px] text-[#D9C8B4] mt-1 uppercase tracking-wider font-semibold">
                Infosys Springboard Internship
              </p>
            </div>
            <button
              onClick={onCloseMobile}
              className="lg:hidden text-[#D9C8B4] hover:text-white p-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-5 overflow-y-auto max-h-[calc(100vh-170px)]">
            {navSections.map((sec) => (
              <div key={sec.title}>
                <h3 className="px-3 text-[10px] font-bold text-[#9E775F] uppercase tracking-wider mb-1.5">
                  {sec.title}
                </h3>
                <div className="space-y-0.5">
                  {sec.items.map((item) => {
                    const active = currentTab === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          onSelectTab(item.id);
                          onCloseMobile();
                        }}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                          active
                            ? 'bg-[#3F281D] text-white shadow-xs border border-[#5C3D2E]'
                            : 'text-[#D9C8B4] hover:bg-[#342219] hover:text-white'
                        }`}
                      >
                        <span className={active ? 'text-[#D9C8B4]' : 'text-[#9E775F]'}>
                          {item.icon}
                        </span>
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>
        </div>

        <div className="p-3 border-t border-[#3F281D] bg-[#231610]">
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#2A1B14] border border-[#3F281D]">
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#D9C8B4]">
              System Active
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="System Online" />
          </div>
        </div>
      </aside>
    </>
  );
};
