import React from 'react';

export function MobileBottomNav({ activeTab, onSelectTab, onOpenAuth, currentUser }) {
  const navItems = [
    { id: 'live', label: 'สด', icon: '📹' },
    { id: 'business', label: 'ธุรกิจ', icon: '🏢' },
    { id: 'benchmark', label: 'เทียบ AI', icon: '⚖️' },
    { id: 'reports', label: 'สถิติ', icon: '📊' },
  ];

  return (
    <nav className="mobile-bottom-nav">
      {navItems.map((item) => {
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectTab(item.id)}
            className={`mobile-nav-btn ${isActive ? 'active' : ''}`}
          >
            <span style={{ fontSize: '1.25rem', marginBottom: '2px' }}>{item.icon}</span>
            <span style={{ fontSize: '0.68rem', fontWeight: isActive ? '800' : '600' }}>{item.label}</span>
          </button>
        );
      })}

      {/* Account / Login Tab */}
      <button
        type="button"
        onClick={onOpenAuth}
        className="mobile-nav-btn"
      >
        <span style={{ fontSize: '1.25rem', marginBottom: '2px' }}>
          {currentUser ? '👤' : '🔐'}
        </span>
        <span style={{ fontSize: '0.68rem', fontWeight: '700', color: currentUser ? '#10b981' : 'var(--text-secondary)' }}>
          {currentUser ? (currentUser.username.substring(0, 6)) : 'ล็อกอิน'}
        </span>
      </button>
    </nav>
  );
}
