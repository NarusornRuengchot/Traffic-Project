import React from 'react';

export function VehicleBreakdown({ classCounts, totalCount }) {
  const classes = [
    { key: 'Car', label: 'Car (รถยนต์)', icon: '🚗', color: '#3b82f6' },
    { key: 'Motorcycle', label: 'Motorcycle (มอเตอร์ไซค์)', icon: '🏍️', color: '#10b981' },
    { key: 'Bus', label: 'Bus (รถบัส)', icon: '🚌', color: '#f59e0b' },
    { key: 'Truck', label: 'Truck (รถบรรทุก)', icon: '🚚', color: '#8b5cf6' }
  ];

  return (
    <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <h3 style={{ fontSize: '0.95rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
        📊 Vehicle Classification
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {classes.map((cls) => {
          const count = classCounts[cls.key] || 0;
          const percentage = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : 0;

          return (
            <div key={cls.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{cls.icon}</span>
                  <span style={{ fontWeight: '600' }}>{cls.label}</span>
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: cls.color }}>
                  {count} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>({percentage}%)</span>
                </span>
              </div>

              {/* Progress Bar */}
              <div style={{
                width: '100%',
                height: '8px',
                borderRadius: '999px',
                backgroundColor: 'var(--bg-input)',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${percentage}%`,
                  height: '100%',
                  backgroundColor: cls.color,
                  borderRadius: '999px',
                  transition: 'width 0.4s ease'
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
