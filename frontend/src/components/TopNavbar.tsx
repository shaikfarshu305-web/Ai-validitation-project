import React from 'react';
import { Menu, Plus, Cpu, Activity } from 'lucide-react';

interface Props {
  pageTitle: string;
  pageSubtitle: string;
  onOpenMobileMenu: () => void;
  onNewVerify: () => void;
  systemStatus?: string;
  currentModel?: string;
}

export const TopNavbar: React.FC<Props> = ({
  pageTitle,
  pageSubtitle,
  onOpenMobileMenu,
  onNewVerify,
  systemStatus = 'ONLINE',
  currentModel = 'Local NLP & Semantic Analyzer',
}) => {
  return (
    <header className="sticky top-0 z-30 bg-[#F7F3EB]/95 backdrop-blur-md border-b border-[#E4D7C5] px-4 lg:px-8 py-3.5 flex items-center justify-between">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded-xl text-[#5C3D2E] hover:bg-[#EDE3D5] transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-lg lg:text-xl font-extrabold text-[#2A1B14] tracking-tight">
            {pageTitle}
          </h2>
          <p className="text-xs text-[#7D543E] font-medium hidden sm:block">
            {pageSubtitle}
          </p>
        </div>
      </div>

      {/* Right: Status Badges & Quick Action */}
      <div className="flex items-center gap-2.5 sm:gap-4">
        {/* Model Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#E4D7C5] text-xs text-[#5C3D2E] font-semibold shadow-xs">
          <Cpu className="w-3.5 h-3.5 text-[#8C5E3C]" />
          <span className="truncate max-w-[170px]">{currentModel}</span>
        </div>

        {/* System Online Status */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-bold shadow-xs">
          <Activity className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
          <span>{systemStatus}</span>
        </div>

        {/* Quick Action Button */}
        <button
          onClick={onNewVerify}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#5C3D2E] to-[#3F281D] hover:from-[#4A3024] hover:to-[#2A1B14] text-white text-xs font-bold shadow-soft transition-all transform active:scale-95 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Verify Response</span>
        </button>
      </div>
    </header>
  );
};
