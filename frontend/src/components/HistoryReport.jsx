import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function HistoryReport() {
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [peakData, setPeakData] = useState(null);
  const [eventsData, setEventsData] = useState({ events: [], total: 0, page: 1, limit: 15, total_pages: 1 });
  const [vehicleFilter, setVehicleFilter] = useState('All');
  const [directionFilter, setDirectionFilter] = useState('All');
  const [isLoading, setIsLoading] = useState(false);
  const [hoveredBar, setHoveredBar] = useState(null);

  // Load available dates on mount
  useEffect(() => {
    async function loadDates() {
      try {
        const res = await api.getReportDates();
        if (res && res.dates) {
          setDates(res.dates);
          if (res.dates.length > 0) {
            setSelectedDate(res.dates[0]);
          }
        }
      } catch (err) {
        console.error('Failed to load report dates:', err);
      }
    }
    loadDates();
  }, []);

  // Fetch peak analysis and historical events when date or filters change
  useEffect(() => {
    async function fetchReportData() {
      setIsLoading(true);
      try {
        const [peakRes, histRes] = await Promise.all([
          api.getPeakHoursReport(selectedDate || null),
          api.getHistoryReport({
            date: selectedDate || null,
            vehicleType: vehicleFilter,
            direction: directionFilter,
            page: eventsData.page || 1,
            limit: 15
          })
        ]);
        setPeakData(peakRes);
        setEventsData(histRes);
      } catch (err) {
        console.error('Failed to fetch report data:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchReportData();
  }, [selectedDate, vehicleFilter, directionFilter, eventsData.page]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= eventsData.total_pages) {
      setEventsData((prev) => ({ ...prev, page: newPage }));
    }
  };

  const hourly = peakData?.hourly_distribution || [];
  const maxHourlyCount = Math.max(5, ...(hourly.map((h) => h.total) || [0]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      {/* Header & Controls */}
      <div className="glass-card" style={{ padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            <span>📊</span> รายงานสถิติจราจรและช่วงเวลาเร่งด่วน (Peak Hours Report)
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            ระบบบันทึกฐานข้อมูล SQLite ถาวรเพื่อการวิเคราะห์ทางวิชาการและโครงงานสัมมนา
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Date Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)' }}>📅 วันที่:</label>
            <select
              className="form-select"
              value={selectedDate}
              onChange={(e) => {
                setSelectedDate(e.target.value);
                setEventsData((prev) => ({ ...prev, page: 1 }));
              }}
              style={{ padding: '8px 12px', fontSize: '0.8rem', minWidth: '150px' }}
            >
              <option value="">ทั้งหมด (All Dates)</option>
              {dates.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Export CSV Button */}
          <a
            href={api.getReportExportUrl(selectedDate)}
            download
            className="btn btn-secondary"
            style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
          >
            <span>📥</span> ดาวน์โหลด CSV
          </a>

          {/* Print Button */}
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => window.print()}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
          >
            <span>🖨️</span> พิมพ์รายงานสรุป
          </button>
        </div>
      </div>

      {/* 4 Academic KPI Highlight Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '16px' }}>
        {/* Total Volume */}
        <div className="glass-card" style={{ padding: '18px', borderLeft: '4px solid #3B82F6' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            🚗 ปริมาณยานพาหนะสะสม
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#3B82F6', marginTop: '6px' }}>
            {peakData ? peakData.total_vehicles.toLocaleString() : '0'} <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>คัน</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            ขาเข้า {peakData?.inbound_percentage || 50}% • ขาออก {peakData?.outbound_percentage || 50}%
          </div>
        </div>

        {/* Busiest Peak Hour */}
        <div className="glass-card" style={{ padding: '18px', borderLeft: '4px solid #EF4444' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            🔥 ช่วงเวลาเร่งด่วนสูงสุด (Peak Hour)
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: '800', color: '#EF4444', marginTop: '6px' }}>
            {peakData?.busiest_hour || 'N/A'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            ปริมาณรถสูงสุด {peakData?.busiest_count || 0} คัน/ชั่วโมง
          </div>
        </div>

        {/* Morning & Evening Windows */}
        <div className="glass-card" style={{ padding: '18px', borderLeft: '4px solid #F59E0B' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            🌅 เช้า vs 🌆 เย็น (Peak Windows)
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#F59E0B', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div>🌅 เช้า: {peakData?.morning_peak || 'N/A'} ({peakData?.morning_peak_count || 0} คัน)</div>
            <div>🌆 เย็น: {peakData?.evening_peak || 'N/A'} ({peakData?.evening_peak_count || 0} คัน)</div>
          </div>
        </div>

        {/* Dominant Vehicle Class */}
        <div className="glass-card" style={{ padding: '18px', borderLeft: '4px solid #10B981' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            🏍️ ยานพาหนะที่พบมากที่สุด
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: '800', color: '#10B981', marginTop: '6px' }}>
            {peakData?.dominant_vehicle || 'None'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            คิดเป็น {peakData?.dominant_percentage || 0}% ของการจราจรทั้งหมด
          </div>
        </div>
      </div>

      {/* Main Charts: 24h Peak Hours Bar Chart + Modal Split */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* 24-Hour Peak Hours SVG Bar Chart */}
        <div className="glass-card" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📈</span> การกระจายตัวของปริมาณรถ 24 ชั่วโมง (Hourly Distribution)
            </h3>
            <div style={{ display: 'flex', gap: '14px', fontSize: '0.75rem', fontWeight: '600' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#3B82F6' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#3B82F6' }}></span>
                ช่วงเวลาปกติ
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#EF4444' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#EF4444' }}></span>
                ช่วงเวลาเร่งด่วน (Peak Hour)
              </span>
            </div>
          </div>

          {/* SVG Bar Chart */}
          <div style={{ position: 'relative', width: '100%', height: '220px' }}>
            <svg width="100%" height="100%" viewBox="0 0 720 220" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                const y = 180 - ratio * 150;
                return (
                  <g key={i}>
                    <line x1="40" y1={y} x2="700" y2={y} stroke="var(--border-color)" strokeDasharray="3 3" opacity="0.6" />
                    <text x="32" y={y + 4} fill="var(--text-secondary)" fontSize="10" textAnchor="end">
                      {Math.round(ratio * maxHourlyCount)}
                    </text>
                  </g>
                );
              })}

              {/* Bars */}
              {hourly.map((h, i) => {
                const barWidth = 20;
                const x = 50 + i * 27;
                const barHeight = maxHourlyCount > 0 ? (h.total / maxHourlyCount) * 150 : 0;
                const y = 180 - barHeight;
                const isPeak = h.is_peak;

                return (
                  <g
                    key={h.hour}
                    onMouseEnter={() => setHoveredBar(h)}
                    onMouseLeave={() => setHoveredBar(null)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Peak Flame Icon / Tag */}
                    {isPeak && h.total > 0 && (
                      <text x={x + barWidth / 2} y={y - 6} fill="#EF4444" fontSize="10" fontWeight="bold" textAnchor="middle">
                        🔥
                      </text>
                    )}

                    {/* Bar Rectangle */}
                    <rect
                      x={x}
                      y={y}
                      width={barWidth}
                      height={Math.max(2, barHeight)}
                      rx="3"
                      fill={isPeak && h.total > 0 ? 'url(#peakGrad)' : 'url(#normalGrad)'}
                      opacity={hoveredBar && hoveredBar.hour !== h.hour ? 0.4 : 1}
                      style={{ transition: 'all 0.2s ease' }}
                    />

                    {/* X-axis labels (every 2 hours) */}
                    {h.hour % 2 === 0 && (
                      <text x={x + barWidth / 2} y="198" fill="var(--text-secondary)" fontSize="10" textAnchor="middle">
                        {h.hour}:00
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Gradients */}
              <defs>
                <linearGradient id="normalGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38BDF8" />
                  <stop offset="100%" stopColor="#2563EB" />
                </linearGradient>
                <linearGradient id="peakGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F87171" />
                  <stop offset="100%" stopColor="#DC2626" />
                </linearGradient>
              </defs>
            </svg>

            {/* Hover Tooltip */}
            {hoveredBar && (
              <div
                style={{
                  position: 'absolute',
                  top: '10px',
                  right: '20px',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '0.75rem',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  pointerEvents: 'none',
                  zIndex: 10
                }}
              >
                <div style={{ fontWeight: '800', color: hoveredBar.is_peak ? '#EF4444' : 'var(--text-primary)', marginBottom: '4px' }}>
                  ⏰ เวลา {hoveredBar.label} {hoveredBar.is_peak ? '(ช่วงเวลาเร่งด่วน)' : ''}
                </div>
                <div>รวม: <strong>{hoveredBar.total}</strong> คัน</div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
                  ขาเข้า: {hoveredBar.inbound} • ขาออก: {hoveredBar.outbound}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  🚗 รถเก๋ง: {hoveredBar.car} • 🏍️ มอเตอร์ไซค์: {hoveredBar.motorcycle}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Split Breakdown */}
        <div className="glass-card" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📊</span> สัดส่วนประเภทยานพาหนะ (Modal Split)
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '6px' }}>
            {peakData && Object.entries(peakData.modal_split || {}).map(([vClass, count]) => {
              const pct = peakData.total_vehicles > 0 ? ((count / peakData.total_vehicles) * 100).toFixed(1) : 0;
              const colors = {
                Car: '#3B82F6',
                Motorcycle: '#10B981',
                Bus: '#F59E0B',
                Truck: '#8B5CF6'
              };
              const icons = {
                Car: '🚗',
                Motorcycle: '🏍️',
                Bus: '🚌',
                Truck: '🚚'
              };
              const color = colors[vClass] || '#64748B';

              return (
                <div key={vClass}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600', marginBottom: '4px' }}>
                    <span>{icons[vClass] || '🚘'} {vClass}</span>
                    <span>{count.toLocaleString()} คัน ({pct}%)</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', backgroundColor: color, borderRadius: '4px', transition: 'width 0.4s ease' }}></div>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: 'auto', padding: '12px', borderRadius: '8px', background: 'rgba(255,255,255,0.03)', fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            💡 <strong>สรุปผลทางสถิติ:</strong> สัดส่วนยานพาหนะประเภท {peakData?.dominant_vehicle} มีอัตราสูงสุด เหมาะสำหรับใช้อ้างอิงการจัดสรรรอบสัญญาณไฟจราจร
          </div>
        </div>
      </div>

      {/* Historical Event Log Table with Filters & Pagination */}
      <div className="glass-card" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', margin: 0 }}>
              📋 รายการตรวจจับยานพาหนะย้อนหลัง (Historical Vehicle Records)
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              บันทึกทั้งหมด {eventsData.total.toLocaleString()} รายการ
            </span>
          </div>

          {/* Filter Bar */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <select
              className="form-select"
              value={vehicleFilter}
              onChange={(e) => {
                setVehicleFilter(e.target.value);
                setEventsData((prev) => ({ ...prev, page: 1 }));
              }}
              style={{ fontSize: '0.75rem', padding: '6px 10px' }}
            >
              <option value="All">ยานพาหนะทั้งหมด</option>
              <option value="Car">เฉพาะรถยนต์ (Car)</option>
              <option value="Motorcycle">เฉพาะมอเตอร์ไซค์ (Motorcycle)</option>
              <option value="Bus">เฉพาะรถบัส (Bus)</option>
              <option value="Truck">เฉพาะรถบรรทุก (Truck)</option>
            </select>

            <select
              className="form-select"
              value={directionFilter}
              onChange={(e) => {
                setDirectionFilter(e.target.value);
                setEventsData((prev) => ({ ...prev, page: 1 }));
              }}
              style={{ fontSize: '0.75rem', padding: '6px 10px' }}
            >
              <option value="All">ทุกทิศทาง (In & Out)</option>
              <option value="Inbound">ขาเข้า (Inbound)</option>
              <option value="Outbound">ขาออก (Outbound)</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px 12px' }}>ID</th>
                <th style={{ padding: '10px 12px' }}>วัน-เวลาจริง (Real-world Time)</th>
                <th style={{ padding: '10px 12px' }}>Vehicle ID</th>
                <th style={{ padding: '10px 12px' }}>ประเภทยานพาหนะ</th>
                <th style={{ padding: '10px 12px' }}>ทิศทางการเดินรถ</th>
                <th style={{ padding: '10px 12px' }}>ระดับการจราจร</th>
              </tr>
            </thead>
            <tbody>
              {eventsData.events.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
                    {isLoading ? '⏳ กำลังดึงข้อมูลจาก SQLite Database...' : 'ไม่มีข้อมูลการตรวจจับสำหรับตัวกรองนี้'}
                  </td>
                </tr>
              ) : (
                eventsData.events.map((ev) => (
                  <tr key={ev.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                      #{ev.id}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: '600' }}>
                      {ev.real_time}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>
                      #{ev.vehicle_id}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: '700',
                        backgroundColor: ev.vehicle_type === 'Car' ? 'rgba(59, 130, 246, 0.15)' :
                                       ev.vehicle_type === 'Motorcycle' ? 'rgba(16, 185, 129, 0.15)' :
                                       ev.vehicle_type === 'Bus' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(139, 92, 246, 0.15)',
                        color: ev.vehicle_type === 'Car' ? '#60A5FA' :
                               ev.vehicle_type === 'Motorcycle' ? '#34D399' :
                               ev.vehicle_type === 'Bus' ? '#FBBF24' : '#A78BFA'
                      }}>
                        {ev.vehicle_type}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        color: ev.direction === 'Inbound' ? '#06b6d4' : '#f97316',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        {ev.direction === 'Inbound' ? '⬇ Inbound' : '⬆ Outbound'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      {ev.traffic_level}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <div>
            หน้า {eventsData.page} จากทั้งหมด {eventsData.total_pages} หน้า
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={eventsData.page <= 1 || isLoading}
              onClick={() => handlePageChange(eventsData.page - 1)}
              style={{ padding: '5px 10px', fontSize: '0.75rem' }}
            >
              ◀ ก่อนหน้า
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={eventsData.page >= eventsData.total_pages || isLoading}
              onClick={() => handlePageChange(eventsData.page + 1)}
              style={{ padding: '5px 10px', fontSize: '0.75rem' }}
            >
              ถัดไป ▶
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
