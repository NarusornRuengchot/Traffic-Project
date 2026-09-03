import React from 'react';

export function Header({ isConnected, isPlaying, isLive, fps, theme, onToggleTheme, activeTab = 'live', onSelectTab }) {
  return (
    <header className="glass-card" style={{ padding: '16px 24px', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, #2563eb, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '22px',
          boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)'
        }}>
          🚗
        </div>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            KU SRC Smart Traffic
            <span style={{ fontSize: '0.75rem', fontWeight: '600', padding: '2px 8px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}>
              v2.3 Live AI + SQLite
            </span>
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Real-time Vehicle Detection, Tracking, Peak Hours & Academic Analytics
          </p>
        </div>
      </div>

      {/* Navigation Tab Switcher */}
      {onSelectTab && (
        <div style={{ display: 'flex', background: 'var(--bg-input)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-color)', gap: '4px' }}>
          <button
            type="button"
            onClick={() => onSelectTab('live')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '700',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'live' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'live' ? '#fff' : 'var(--text-secondary)'
            }}
          >
            📹 หน้าตรวจจับสด (Live)
          </button>
          <button
            type="button"
            onClick={() => onSelectTab('reports')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '700',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'reports' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'reports' ? '#fff' : 'var(--text-secondary)'
            }}
          >
            📊 สถิติย้อนหลังและรายงาน (Reports)
          </button>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {/* Real-time Live Camera Badge */}
        {isPlaying && isLive && (
          <div style={{
            fontSize: '0.8rem',
            fontWeight: '700',
            padding: '6px 12px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#ef4444',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444', display: 'inline-block' }}></span>
            🔴 LIVE CAMERA
          </div>
        )}

        {/* Connection Status */}
        <div className={`badge ${isConnected ? 'badge-live' : 'badge-danger'}`} style={{
          background: isConnected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          color: isConnected ? '#10b981' : '#ef4444',
          border: `1px solid ${isConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
        }}>
          <span className="badge-pulse"></span>
          {isConnected ? 'LIVE WS CONNECTED' : 'DISCONNECTED'}
        </div>

        {/* Stream FPS */}
        {isPlaying && (
          <div style={{
            fontSize: '0.8rem',
            fontWeight: '600',
            padding: '6px 12px',
            borderRadius: '8px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            fontFamily: 'var(--font-mono)'
          }}>
            ⚡ {fps} FPS
          </div>
        )}

        {/* Theme Switcher */}
        <button
          onClick={onToggleTheme}
          className="btn btn-secondary"
          style={{ padding: '8px 12px', fontSize: '1.1rem' }}
          title="Toggle Dark/Light Mode"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  );
}
