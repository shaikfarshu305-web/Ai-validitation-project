import React from 'react';
import { Target, CheckCircle, ShieldAlert, Layers } from 'lucide-react';

interface Props {
  dimension: 'relevance' | 'accuracy' | 'hallucination' | 'completeness';
  title: string;
  score: number; // 0 - 5
  description: string;
  weight?: number; // e.g. 0.35
  onClick?: () => void;
  isActive?: boolean;
}

export const DimensionCard: React.FC<Props> = ({
  dimension,
  title,
  score,
  description,
  weight,
  onClick,
  isActive = false,
}) => {
  const percentage = Math.round((score / 5) * 100);

  const icons = {
    relevance: <Target className="w-5 h-5 text-[#8C5E3C]" />,
    accuracy: <CheckCircle className="w-5 h-5 text-emerald-600" />,
    hallucination: <ShieldAlert className="w-5 h-5 text-rose-600" />,
    completeness: <Layers className="w-5 h-5 text-amber-700" />,
  };

  let statusBadge = {
    text: 'High',
    color: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  };

  if (dimension === 'hallucination') {
    // For hallucination, score is Hallucination Safety (5 = clean/safe, 0 = severe hallucination)
    if (score >= 4.0) {
      statusBadge = { text: 'Low Risk', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    } else if (score >= 2.5) {
      statusBadge = { text: 'Medium Risk', color: 'bg-amber-100 text-amber-800 border-amber-300' };
    } else {
      statusBadge = { text: 'High Risk', color: 'bg-rose-100 text-rose-800 border-rose-300' };
    }
  } else {
    if (score >= 4.0) {
      statusBadge = { text: 'Strong', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    } else if (score >= 2.8) {
      statusBadge = { text: 'Moderate', color: 'bg-amber-100 text-amber-800 border-amber-300' };
    } else {
      statusBadge = { text: 'Deficient', color: 'bg-rose-100 text-rose-800 border-rose-300' };
    }
  }

  // Progress bar color
  let barColor = 'bg-emerald-600';
  if (percentage < 55) barColor = 'bg-rose-600';
  else if (percentage < 75) barColor = 'bg-amber-600';

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl p-5 border transition-all duration-200 cursor-pointer ${
        isActive
          ? 'bg-[#FFFDFB] border-[#7D543E] shadow-medium ring-2 ring-[#7D543E]/20'
          : 'bg-white border-[#E4D7C5] hover:border-[#C9B59F] hover:shadow-soft'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-[#F7F3EB] border border-[#E8DFC8]">
            {icons[dimension]}
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#2A1B14]">{title}</h4>
            {weight && (
              <span className="text-[11px] font-medium text-[#7D543E]">
                Weight: {Math.round(weight * 100)}%
              </span>
            )}
          </div>
        </div>
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${statusBadge.color}`}>
          {statusBadge.text}
        </span>
      </div>

      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-black text-[#2A1B14]">
            {score.toFixed(1)}
          </span>
          <span className="text-xs font-semibold text-[#9E775F]">/ 5.0</span>
        </div>
        <span className="text-xs font-bold text-[#5C3D2E]">{percentage}%</span>
      </div>

      {/* Progress track */}
      <div className="w-full h-2 bg-[#F1ECE2] rounded-full overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all duration-800 ease-out ${barColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="text-xs text-[#5C3D2E] line-clamp-2 leading-relaxed">
        {description}
      </p>
    </div>
  );
};
