import React from 'react';

export function Header({
  isConnected,
  isPlaying,
  isLive,
  fps,
  theme,
  onToggleTheme,
  activeTab = 'live',
  onSelectTab,
  currentUser,
  onOpenAuth
}) {
  return (
    <header className="glass-card main-header">
      <div className="header-brand" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="header-logo" style={{
          width: '42px',
          height: '42px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, #2563eb, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)',
          flexShrink: 0
        }}>
          🚗
        </div>
        <div>
          <h1 className="header-title" style={{ fontSize: '1.2rem', fontWeight: '800', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            KU SRC Smart Traffic
            <span className="header-badge" style={{ fontSize: '0.72rem', fontWeight: '700', padding: '2px 8px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' }}>
              v2.4 Mobile
            </span>
          </h1>
          <p className="header-sub" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            Real-time Vehicle AI, Business Footfall Analytics & Multi-Branch CCTV
          </p>
        </div>
      </div>

      {/* Navigation Tab Switcher */}
      {onSelectTab && (
        <div className="desktop-nav-tabs" style={{ display: 'flex', background: 'var(--bg-input)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-color)', gap: '4px' }}>
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
            onClick={() => onSelectTab('business')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '700',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'business' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'business' ? '#fff' : 'var(--text-secondary)'
            }}
          >
            🏢 ข้อมูลธุรกิจ (Business)
          </button>
          <button
            type="button"
            onClick={() => onSelectTab('benchmark')}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '700',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeTab === 'benchmark' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'benchmark' ? '#fff' : 'var(--text-secondary)'
            }}
          >
            ⚖️ เปรียบเทียบโมเดล AI (Benchmark)
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

        {/* User Auth Profile Button */}
        <button
          onClick={onOpenAuth}
          className="btn"
          style={{
            padding: '8px 14px',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: currentUser ? 'rgba(37, 99, 235, 0.15)' : 'var(--bg-input)',
            color: currentUser ? '#60a5fa' : 'var(--text-main)',
            border: currentUser ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid var(--border-color)',
            borderRadius: '10px'
          }}
          title={currentUser ? `บัญชี: ${currentUser.full_name || currentUser.username} (${currentUser.role})` : "เข้าสู่ระบบ / จัดการบัญชี"}
        >
          <span>{currentUser ? (currentUser.role === 'admin' ? '👑' : '👤') : '🔐'}</span>
          <span style={{ fontWeight: 600 }}>
            {currentUser ? currentUser.username : 'เข้าสู่ระบบ'}
          </span>
          {currentUser && (
            <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)' }}>
              {currentUser.role}
            </span>
          )}
        </button>

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
