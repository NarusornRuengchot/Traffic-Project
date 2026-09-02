import React from 'react';

export function MetricCards({ telemetry }) {
  const cards = [
    {
      title: 'Inbound Flow (เข้าเมือง)',
      value: telemetry.inbound_count,
      subValue: `Active: ${telemetry.inbound_active} veh`,
      icon: '⬅️',
      color: '#06b6d4',
      bgGlow: 'rgba(6, 182, 212, 0.15)'
    },
    {
      title: 'Outbound Flow (ออกเมือง)',
      value: telemetry.outbound_count,
      subValue: `Active: ${telemetry.outbound_active} veh`,
      icon: '➡️',
      color: '#f97316',
      bgGlow: 'rgba(249, 115, 22, 0.15)'
    },
    {
      title: 'Total Passed (ยอดสะสม)',
      value: telemetry.total_count,
      subValue: `Time: ${telemetry.real_time}`,
      icon: '🚗',
      color: '#3b82f6',
      bgGlow: 'rgba(59, 130, 246, 0.15)'
    },
    {
      title: 'Active Vehicles (บนถนน)',
      value: telemetry.active_vehicles,
      subValue: `Stall Ratio: ${(telemetry.stall_ratio * 100).toFixed(0)}%`,
      icon: '⚡',
      color: '#8b5cf6',
      bgGlow: 'rgba(139, 92, 246, 0.15)'
    },
    {
      title: 'Congestion Level (สภาพจราจร)',
      value: `${telemetry.traffic_level_emoji} ${telemetry.traffic_level_en}`,
      subValue: `${telemetry.traffic_level_th} (Score: ${telemetry.density_score})`,
      icon: '🚦',
      color: telemetry.traffic_level_color || '#10b981',
      bgGlow: `${telemetry.traffic_level_color || '#10b981'}25`
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px',
      marginBottom: '20px'
    }}>
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="glass-card"
          style={{
            padding: '16px 20px',
            position: 'relative',
            overflow: 'hidden',
            borderLeft: `4px solid ${card.color}`
          }}
        >
          {/* Subtle Background Glow */}
          <div style={{
            position: 'absolute',
            top: '-20px',
            right: '-20px',
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: card.bgGlow,
            filter: 'blur(20px)',
            pointerEvents: 'none'
          }} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {card.title}
            </span>
            <span style={{ fontSize: '1.2rem' }}>{card.icon}</span>
          </div>

          <div style={{ fontSize: '1.75rem', fontWeight: '800', color: card.color, lineHeight: '1.2', fontFamily: 'var(--font-mono)' }}>
            {card.value}
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {card.subValue}
          </div>
        </div>
      ))}
    </div>
  );
}
