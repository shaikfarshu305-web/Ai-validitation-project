import React from 'react';
import { ShieldCheck, HelpCircle, ShieldAlert } from 'lucide-react';

interface Props {
  status: 'supported' | 'unsupported' | 'contradicted' | string;
}

export const ClaimBadge: React.FC<Props> = ({ status }) => {
  const s = status.toLowerCase();

  if (s === 'supported') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
        SUPPORTED
      </span>
    );
  }

  if (s === 'contradicted') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
        CONTRADICTED
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
      <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
      UNSUPPORTED
    </span>
  );
};
