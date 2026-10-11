import React from 'react';

interface Props {
  score: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
}

export const ScoreGauge: React.FC<Props> = ({
  score,
  size = 140,
  strokeWidth = 10,
  showLabel = true,
}) => {
  const normalizedScore = Math.max(0, Math.min(100, score));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalizedScore / 100) * circumference;

  let strokeColor = '#15803D'; // Green / PASS
  let bgColor = '#DCFCE7';

  if (normalizedScore < 50) {
    strokeColor = '#B91C1C'; // Red / FAIL
    bgColor = '#FEE2E2';
  } else if (normalizedScore < 75) {
    strokeColor = '#B45309'; // Amber / NEEDS IMPROVEMENT
    bgColor = '#FEF3C7';
  }

  return (
    <div className="relative inline-flex flex-col items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#E5DEC9"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Colored progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      {/* Centered Score text */}
      <div className="absolute flex flex-col items-center justify-center text-center">
        <span className="text-3xl font-extrabold text-[#2A1B14] tracking-tight">
          {normalizedScore}
        </span>
        <span className="text-[11px] font-semibold text-[#7D543E] uppercase tracking-wider">
          / 100
        </span>
      </div>
      {showLabel && (
        <span className="mt-2 text-xs font-medium text-[#5C3D2E]">
          Overall Score
        </span>
      )}
    </div>
  );
};
