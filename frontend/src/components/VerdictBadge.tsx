import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

interface Props {
  verdict: 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL' | string;
  size?: 'sm' | 'md' | 'lg';
}

export const VerdictBadge: React.FC<Props> = ({ verdict, size = 'md' }) => {
  const v = verdict.toUpperCase();

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-semibold',
    lg: 'px-3.5 py-1.5 text-sm font-bold',
  }[size];

  if (v === 'PASS') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 ${sizeClasses}`}>
        <CheckCircle2 className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
        PASS
      </span>
    );
  }

  if (v === 'NEEDS_IMPROVEMENT' || v === 'NEEDS IMPROVEMENT') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 ${sizeClasses}`}>
        <AlertTriangle className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
        NEEDS IMPROVEMENT
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300 ${sizeClasses}`}>
      <XCircle className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
      FAIL
    </span>
  );
};
