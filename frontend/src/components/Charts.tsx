import React from 'react';

// 1. Trend Line Chart (Score Trend Over Time)
export const TrendLineChart: React.FC<{ data: Array<{ date: string; score: number }> }> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-xs text-[#9E775F]">
        No chronological trend data available yet
      </div>
    );
  }

  const width = 500;
  const height = 180;
  const padding = 30;

  const minScore = 0;
  const maxScore = 100;

  const points = data.map((d, i) => {
    const x = padding + (i / Math.max(1, data.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((d.score - minScore) / (maxScore - minScore)) * (height - 2 * padding);
    return { x, y, ...d };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x},${height - padding} L ${points[0].x},${height - padding} Z`;

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48">
        <defs>
          <linearGradient id="scoreTrendGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#8C5E3C" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#8C5E3C" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Horizontal gridlines */}
        {[25, 50, 75, 100].map((val) => {
          const y = height - padding - (val / 100) * (height - 2 * padding);
          return (
            <g key={val}>
              <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#E8DFC8" strokeDasharray="3 3" />
              <text x={padding - 6} y={y + 3} textAnchor="end" fontSize="9" fill="#9E775F" fontFamily="sans-serif">
                {val}
              </text>
            </g>
          );
        })}

        {/* Shaded Area */}
        <path d={areaD} fill="url(#scoreTrendGrad)" />

        {/* Line Stroke */}
        <path d={pathD} fill="none" stroke="#7D543E" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data points */}
        {points.map((pt, idx) => (
          <g key={idx} className="group">
            <circle cx={pt.x} cy={pt.y} r="4" fill="#FFFFFF" stroke="#5C3D2E" strokeWidth="2" className="cursor-pointer" />
            <title>{`${pt.date}: ${pt.score}/100`}</title>
          </g>
        ))}
      </svg>
    </div>
  );
};

// 2. Dimension Comparison Horizontal Bar Chart
export const DimensionComparisonBarChart: React.FC<{
  dimensions: { Accuracy: number; Relevance: number; Completeness: number; HallucinationSafety: number };
}> = ({ dimensions }) => {
  const items = [
    { label: 'Accuracy', value: dimensions?.Accuracy || 0, color: 'bg-emerald-600', max: 100 },
    { label: 'Relevance', value: dimensions?.Relevance || 0, color: 'bg-[#8C5E3C]', max: 100 },
    { label: 'Hallucination Safety', value: dimensions?.HallucinationSafety || 0, color: 'bg-teal-600', max: 100 },
    { label: 'Completeness', value: dimensions?.Completeness || 0, color: 'bg-amber-600', max: 100 },
  ];

  return (
    <div className="space-y-3.5 py-1">
      {items.map((item) => (
        <div key={item.label}>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold text-[#2A1B14]">{item.label}</span>
            <span className="font-bold text-[#5C3D2E]">{item.value.toFixed(1)}%</span>
          </div>
          <div className="w-full h-2.5 bg-[#F1ECE2] rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-800 ${item.color}`}
              style={{ width: `${Math.min(100, Math.max(0, item.value))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

// 3. Verdict Distribution Donut Chart
export const VerdictDistributionDonutChart: React.FC<{
  distribution: { PASS: number; NEEDS_IMPROVEMENT: number; FAIL: number };
}> = ({ distribution }) => {
  const p = distribution?.PASS || 0;
  const n = distribution?.NEEDS_IMPROVEMENT || 0;
  const f = distribution?.FAIL || 0;
  const total = p + n + f;

  if (total === 0) {
    return <div className="h-44 flex items-center justify-center text-xs text-[#9E775F]">No evaluations yet</div>;
  }

  const pPct = (p / total) * 100;
  const nPct = (n / total) * 100;
  const fPct = (f / total) * 100;

  // SVG Donut Calculations
  const size = 130;
  const stroke = 18;
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;

  const pOffset = 0;
  const pLen = (pPct / 100) * circ;

  const nOffset = -pLen;
  const nLen = (nPct / 100) * circ;

  const fOffset = -(pLen + nLen);
  const fLen = (fPct / 100) * circ;

  return (
    <div className="flex items-center justify-around py-2">
      <div className="relative">
        <svg width={size} height={size} className="transform -rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} stroke="#F1ECE2" strokeWidth={stroke} fill="transparent" />
          {/* Pass Segment */}
          {p > 0 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#15803D"
              strokeWidth={stroke}
              fill="transparent"
              strokeDasharray={`${pLen} ${circ}`}
              strokeDashoffset={pOffset}
            />
          )}
          {/* Needs Improvement Segment */}
          {n > 0 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#B45309"
              strokeWidth={stroke}
              fill="transparent"
              strokeDasharray={`${nLen} ${circ}`}
              strokeDashoffset={nOffset}
            />
          )}
          {/* Fail Segment */}
          {f > 0 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="#B91C1C"
              strokeWidth={stroke}
              fill="transparent"
              strokeDasharray={`${fLen} ${circ}`}
              strokeDashoffset={fOffset}
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-xl font-black text-[#2A1B14]">{total}</span>
          <span className="text-[10px] font-semibold text-[#7D543E] uppercase">Evals</span>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
          <span className="text-[#2A1B14] font-medium">Pass:</span>
          <span className="font-bold text-[#2A1B14]">{p} ({Math.round(pPct)}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-600" />
          <span className="text-[#2A1B14] font-medium">Needs Impr:</span>
          <span className="font-bold text-[#2A1B14]">{n} ({Math.round(nPct)}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-600" />
          <span className="text-[#2A1B14] font-medium">Fail:</span>
          <span className="font-bold text-[#2A1B14]">{f} ({Math.round(fPct)}%)</span>
        </div>
      </div>
    </div>
  );
};
