import React from 'react';

export function MetricCards({ telemetry }) {
  const incidentCount = telemetry.active_incidents ? telemetry.active_incidents.length : 0;
  const avgSpeed = telemetry.avg_speed_kmh !== undefined ? telemetry.avg_speed_kmh : 0.0;

  const cards = [
    {
      title: 'Inbound Flow (เข้าเมือง)',
      value: telemetry.inbound_count ?? 0,
      subValue: `Active: ${telemetry.inbound_active ?? 0} veh`,
      icon: '⬅️',
      color: '#06b6d4',
      bgGlow: 'rgba(6, 182, 212, 0.15)'
    },
    {
      title: 'Outbound Flow (ออกเมือง)',
      value: telemetry.outbound_count ?? 0,
      subValue: `Active: ${telemetry.outbound_active ?? 0} veh`,
      icon: '➡️',
      color: '#f97316',
      bgGlow: 'rgba(249, 115, 22, 0.15)'
    },
    {
      title: 'Total Passed (ยอดสะสม)',
      value: telemetry.total_count ?? 0,
      subValue: `Time: ${telemetry.real_time || '00:00:00'}`,
      icon: '🚗',
      color: '#3b82f6',
      bgGlow: 'rgba(59, 130, 246, 0.15)'
    },
    {
      title: 'Avg Speed (ความเร็วเฉลี่ย)',
      value: `${avgSpeed} km/h`,
      subValue: `Stall: ${((telemetry.stall_ratio || 0) * 100).toFixed(0)}%`,
      icon: '🏎️',
      color: avgSpeed > 45 ? '#10b981' : avgSpeed > 20 ? '#f59e0b' : '#ef4444',
      bgGlow: 'rgba(16, 185, 129, 0.15)'
    },
    {
      title: 'Congestion (สภาพจราจร)',
      value: `${telemetry.traffic_level_emoji || '🟢'} ${telemetry.traffic_level_en || 'Smooth'}`,
      subValue: `${telemetry.traffic_level_th || 'คล่องตัว'} (Score: ${telemetry.density_score || 0})`,
      icon: '🚦',
      color: telemetry.traffic_level_color || '#10b981',
      bgGlow: `${telemetry.traffic_level_color || '#10b981'}25`
    },
    {
      title: 'Incidents (เหตุการณ์ผิดปกติ)',
      value: `${incidentCount} จุด`,
      subValue: incidentCount > 0 ? '⚠️ ตรวจพบรถย้อนศร/จอดแช่' : '🛡️ สภาพการเดินรถปกติ',
      icon: incidentCount > 0 ? '🚨' : '🛡️',
      color: incidentCount > 0 ? '#ef4444' : '#10b981',
      bgGlow: incidentCount > 0 ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.15)'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: '14px',
      marginBottom: '20px'
    }}>
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="glass-card"
          style={{
            padding: '16px 18px',
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
            <span style={{ fontSize: '0.72rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {card.title}
            </span>
            <span style={{ fontSize: '1.2rem' }}>{card.icon}</span>
          </div>

          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: card.color, lineHeight: '1.2', fontFamily: 'var(--font-mono)' }}>
            {card.value}
          </div>

          <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {card.subValue}
          </div>
        </div>
      ))}
    </div>
  );
}
