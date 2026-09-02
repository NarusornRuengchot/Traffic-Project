import React, { useState, useEffect } from 'react';

export function AnalyticsCharts({ telemetry, isPlaying }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!isPlaying) return;

    setHistory((prev) => {
      const newPoint = {
        time: telemetry.real_time || '00:00:00',
        inbound: telemetry.inbound_count || 0,
        outbound: telemetry.outbound_count || 0,
        active: telemetry.active_vehicles || 0,
        density: telemetry.density_score || 0
      };

      const updated = [...prev, newPoint];
      return updated.slice(-30); // Keep last 30 data points
    });
  }, [telemetry.real_time, isPlaying]);

  const width = 500;
  const height = 140;
  const padding = 25;

  const maxVal = Math.max(
    5,
    ...history.map((d) => Math.max(d.inbound, d.outbound, d.active))
  );

  const getY = (val) => {
    return height - padding - (val / maxVal) * (height - 2 * padding);
  };

  const getX = (idx) => {
    if (history.length <= 1) return padding;
    return padding + (idx / (history.length - 1)) * (width - 2 * padding);
  };

  const buildPath = (key) => {
    if (history.length === 0) return '';
    return history.reduce((acc, pt, idx) => {
      const x = getX(idx);
      const y = getY(pt[key]);
      return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
    }, '');
  };

  return (
    <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
          📈 Live Traffic Trend (Flow & Density)
        </h3>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', fontWeight: '600' }}>
          <span style={{ color: '#06b6d4' }}>● Inbound</span>
          <span style={{ color: '#f97316' }}>● Outbound</span>
          <span style={{ color: '#8b5cf6' }}>● Active</span>
        </div>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
          <defs>
            <linearGradient id="gradCyan" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="var(--border-color)" strokeDasharray="3 3" />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--border-color)" strokeDasharray="3 3" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" />

          {/* Y Axis text */}
          <text x={padding - 6} y={padding + 4} fill="var(--text-muted)" fontSize="9" textAnchor="end">{maxVal}</text>
          <text x={padding - 6} y={height - padding} fill="var(--text-muted)" fontSize="9" textAnchor="end">0</text>

          {/* SVG Lines */}
          {history.length > 1 && (
            <>
              {/* Inbound Line */}
              <path d={buildPath('inbound')} fill="none" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              {/* Outbound Line */}
              <path d={buildPath('outbound')} fill="none" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              {/* Active Vehicles Line */}
              <path d={buildPath('active')} fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="4 2" strokeLinecap="round" />
            </>
          )}

          {history.length <= 1 && (
            <text x={width / 2} y={height / 2} fill="var(--text-muted)" fontSize="11" textAnchor="middle">
              Waiting for live data points...
            </text>
          )}
        </svg>
      </div>
    </div>
  );
}
