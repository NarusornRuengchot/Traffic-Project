import React from 'react';

export function MobileBottomNav({ activeTab, onSelectTab, onOpenAuth, currentUser }) {
  const navItems = [
    { id: 'live', label: 'กล้องสด', icon: '📹', badge: 'LIVE' },
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
            aria-label={item.label}
          >
            <div className="mobile-icon-wrapper">
              <span className="mobile-nav-icon">{item.icon}</span>
              {item.badge && item.id === 'live' && (
                <span className="mobile-nav-live-dot" />
              )}
            </div>
            <span className="mobile-nav-label">{item.label}</span>
            {isActive && <span className="mobile-active-pill" />}
          </button>
        );
      })}

      {/* Account / Profile Button */}
      <button
        type="button"
        onClick={onOpenAuth}
        className="mobile-nav-btn"
        aria-label="จัดการบัญชี"
      >
        <div className="mobile-icon-wrapper">
          <span className="mobile-nav-icon">
            {currentUser ? (currentUser.role === 'admin' ? '👑' : '👤') : '🔐'}
          </span>
          {currentUser && <span className="mobile-user-online-dot" />}
        </div>
        <span
          className="mobile-nav-label"
          style={{
            color: currentUser ? 'var(--accent-primary)' : 'inherit',
            fontWeight: currentUser ? '700' : '600'
          }}
        >
          {currentUser ? (currentUser.username.length > 5 ? `${currentUser.username.slice(0, 5)}..` : currentUser.username) : 'บัญชี'}
        </span>
      </button>
    </nav>
  );
}
