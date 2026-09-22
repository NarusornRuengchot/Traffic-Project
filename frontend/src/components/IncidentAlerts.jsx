import React, { useState } from 'react';

export function IncidentAlerts({ incidents = [] }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [dismissedIds, setDismissedIds] = useState(new Set());

  const activeAlerts = incidents.filter((_, idx) => !dismissedIds.has(idx));

  if (!incidents || incidents.length === 0) {
    return null;
  }

  const handleDismiss = (idx) => {
    setDismissedIds(prev => new Set([...prev, idx]));
  };

  const handleClearAll = () => {
    setDismissedIds(new Set(incidents.map((_, idx) => idx)));
  };

  const getIncidentIcon = (type) => {
    switch (type) {
      case 'wrong_way':
        return '⛔';
      case 'stalled':
        return '⚠️';
      case 'speeding':
        return '🚨';
      default:
        return '🔔';
    }
  };

  const getIncidentBadgeStyle = (type) => {
    switch (type) {
      case 'wrong_way':
        return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#ef4444' };
      case 'stalled':
        return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', text: '#f59e0b' };
      case 'speeding':
        return { bg: 'rgba(236, 72, 153, 0.15)', border: '#ec4899', text: '#ec4899' };
      default:
        return { bg: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6', text: '#3b82f6' };
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        border: '1px solid rgba(239, 68, 68, 0.35)',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 8px 24px rgba(239, 68, 68, 0.12)',
        animation: 'fadeIn 0.3s ease-out'
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          cursor: 'pointer'
        }}
        onClick={() => setIsExpanded(prev => !prev)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem', animation: 'pulse 1.5s infinite' }}>🚨</span>
          <span style={{ fontWeight: '700', fontSize: '0.9rem', color: '#ef4444' }}>
            ตรวจพบเหตุการณ์ผิดปกติ ({activeAlerts.length})
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {activeAlerts.length > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleClearAll();
              }}
              style={{
                background: 'none',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '6px',
                padding: '2px 8px',
                fontSize: '0.72rem',
                color: '#ef4444',
                cursor: 'pointer'
              }}
            >
              ล้างทั้งหมด
            </button>
          )}
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            {isExpanded ? '▲ ซ่อน' : '▼ ดูรายการ'}
          </span>
        </div>
      </div>

      {/* Alert List Body */}
      {isExpanded && activeAlerts.length > 0 && (
        <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
          {activeAlerts.map((inc, idx) => {
            const style = getIncidentBadgeStyle(inc.incident_type);
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  backgroundColor: style.bg,
                  border: `1px solid ${style.border}40`,
                  borderRadius: '8px',
                  fontSize: '0.82rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '1.1rem' }}>{getIncidentIcon(inc.incident_type)}</span>
                  <div>
                    <div style={{ fontWeight: '600', color: style.text }}>
                      {inc.message || `${inc.incident_type} detected`}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      เวลา {inc.real_time || 'N/A'} • ความเร็ว {inc.speed_kmh} km/h • ID #{inc.vehicle_id}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDismiss(idx)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    padding: '2px 6px'
                  }}
                  title="ปิดการแจ้งเตือนนี้"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
