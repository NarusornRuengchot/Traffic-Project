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
        density: telemetry.density_score || 0,
        speed: telemetry.avg_speed_kmh || 0
      };

      const updated = [...prev, newPoint];
      return updated.slice(-30); // Keep last 30 data points
    });
  }, [telemetry.real_time, isPlaying]);

  const width = 500;
  const height = 125;
  const padding = 25;

  const maxVal = Math.max(
    5,
    ...history.map((d) => Math.max(d.inbound, d.outbound, d.active))
  );

  const getY = (val) => {
    return height - padding - (val / maxVal) * (height - 2 * padding);
  };

  const maxSpeed = Math.max(
    60,
    ...history.map((d) => d.speed)
  );

  const getSpeedY = (val) => {
    return height - padding - (val / maxSpeed) * (height - 2 * padding);
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

  const buildSpeedPath = () => {
    if (history.length === 0) return '';
    return history.reduce((acc, pt, idx) => {
      const x = getX(idx);
      const y = getSpeedY(pt.speed);
      return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
    }, '');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* 1. Traffic Flow & Volume Chart */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
            📈 Traffic Flow Trend
          </h3>
          <div style={{ display: 'flex', gap: '10px', fontSize: '0.72rem', fontWeight: '600' }}>
            <span style={{ color: '#06b6d4' }}>● Inbound</span>
            <span style={{ color: '#f97316' }}>● Outbound</span>
            <span style={{ color: '#8b5cf6' }}>● Active</span>
          </div>
        </div>

        <div style={{ width: '100%', overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
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
                <path d={buildPath('inbound')} fill="none" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d={buildPath('outbound')} fill="none" stroke="#f97316" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d={buildPath('active')} fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="4 2" strokeLinecap="round" />
              </>
            )}

            {history.length <= 1 && (
              <text x={width / 2} y={height / 2} fill="var(--text-muted)" fontSize="11" textAnchor="middle">
                Waiting for live flow data...
              </text>
            )}
          </svg>
        </div>
      </div>

      {/* 2. Speed Telemetry Chart */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
            🏎️ Average Speed Telemetry
          </h3>
          <div style={{ display: 'flex', gap: '10px', fontSize: '0.72rem', fontWeight: '600' }}>
            <span style={{ color: '#10b981' }}>● Speed ({telemetry.avg_speed_kmh || 0} km/h)</span>
            <span style={{ color: '#ec4899' }}>-- Limit (50 km/h)</span>
          </div>
        </div>

        <div style={{ width: '100%', overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
            <defs>
              <linearGradient id="gradSpeed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid lines */}
            <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="var(--border-color)" strokeDasharray="3 3" />
            <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--border-color)" strokeDasharray="3 3" />
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" />

            {/* Speed Limit (50 km/h) Reference Line */}
            {maxSpeed >= 50 && (
              <line
                x1={padding}
                y1={getSpeedY(50)}
                x2={width - padding}
                y2={getSpeedY(50)}
                stroke="#ec4899"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
            )}

            {/* Y Axis text */}
            <text x={padding - 6} y={padding + 4} fill="var(--text-muted)" fontSize="9" textAnchor="end">{Math.round(maxSpeed)}</text>
            <text x={padding - 6} y={height - padding} fill="var(--text-muted)" fontSize="9" textAnchor="end">0</text>

            {/* Speed Curve */}
            {history.length > 1 && (
              <path d={buildSpeedPath()} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            )}

            {history.length <= 1 && (
              <text x={width / 2} y={height / 2} fill="var(--text-muted)" fontSize="11" textAnchor="middle">
                Waiting for speed samples...
              </text>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}
