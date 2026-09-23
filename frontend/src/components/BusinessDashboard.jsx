import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function BusinessDashboard({ currentUser, onOpenAuthModal }) {
  const [businesses, setBusinesses] = useState([]);
  const [selectedBizId, setSelectedBizId] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState('');
  const [dates, setDates] = useState([]);

  // Modals for user to enter their own business data
  const [showAddBizModal, setShowAddBizModal] = useState(false);
  const [showAddCamModal, setShowAddCamModal] = useState(false);

  // New Business Form State
  const [newBiz, setNewBiz] = useState({
    name: '',
    business_type: 'retail',
    branch_code: '',
    address: '',
    contact_email: '',
    contact_phone: '',
    opening_hour: 10,
    closing_hour: 22,
    target_hourly_traffic: 120
  });

  // New Camera Form State
  const [newCam, setNewCam] = useState({
    name: '',
    stream_url: '',
    camera_type: 'entrance',
    location_note: ''
  });

  const [formMsg, setFormMsg] = useState(null);

  // Load businesses & available dates
  useEffect(() => {
    loadBusinesses();
    loadDates();
  }, []);

  const loadDates = async () => {
    try {
      const res = await api.getReportDates();
      if (res && res.dates) {
        setDates(res.dates);
        if (res.dates.length > 0 && !selectedDate) {
          setSelectedDate(res.dates[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load dates', err);
    }
  };

  const loadBusinesses = async () => {
    try {
      const res = await api.getBusinesses();
      if (res && res.businesses) {
        setBusinesses(res.businesses);
        if (res.businesses.length > 0 && !selectedBizId) {
          setSelectedBizId(res.businesses[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load businesses', err);
    }
  };

  // Fetch analytics when business or date changes
  useEffect(() => {
    async function fetchAnalytics() {
      setIsLoading(true);
      try {
        const data = await api.getBusinessDashboard(selectedBizId, selectedDate || null);
        setAnalytics(data);
      } catch (err) {
        console.error('Failed to fetch business analytics', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchAnalytics();
  }, [selectedBizId, selectedDate]);

  const handleCreateBusiness = async (e) => {
    e.preventDefault();
    setFormMsg(null);
    try {
      const res = await api.createBusiness(newBiz);
      if (res && res.business_id) {
        setShowAddBizModal(false);
        setNewBiz({
          name: '',
          business_type: 'retail',
          branch_code: '',
          address: '',
          contact_email: '',
          contact_phone: '',
          opening_hour: 10,
          closing_hour: 22,
          target_hourly_traffic: 120
        });
        await loadBusinesses();
        setSelectedBizId(res.business_id);
      }
    } catch (err) {
      setFormMsg(err.message || 'บันทึกข้อมูลธุรกิจไม่สำเร็จ');
    }
  };

  const handleCreateCamera = async (e) => {
    e.preventDefault();
    setFormMsg(null);
    try {
      await api.createBusinessCamera({
        ...newCam,
        business_id: selectedBizId
      });
      setShowAddCamModal(false);
      setNewCam({
        name: '',
        stream_url: '',
        camera_type: 'entrance',
        location_note: ''
      });
      // reload analytics
      const data = await api.getBusinessDashboard(selectedBizId, selectedDate || null);
      setAnalytics(data);
      loadBusinesses();
    } catch (err) {
      setFormMsg(err.message || 'บันทึกกล้องไม่สำเร็จ');
    }
  };

  const handleDeleteCamera = async (camId) => {
    if (!window.confirm('คุณแน่ใจหรือไม่ว่าต้องการลบกล้องนี้?')) return;
    try {
      await api.deleteBusinessCamera(camId);
      const data = await api.getBusinessDashboard(selectedBizId, selectedDate || null);
      setAnalytics(data);
      loadBusinesses();
    } catch (err) {
      alert('ไม่สามารถลบกล้องได้: ' + err.message);
    }
  };

  const currentBiz = analytics?.business || {};
  const kpis = analytics?.kpis || {};
  const hourly = analytics?.hourly_traffic || [];
  const maxHourlyTraffic = Math.max(10, ...hourly.map((h) => h.total));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. Executive Top Bar & Branch Selector */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '28px' }}>🏢</span>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontWeight: '800', letterSpacing: '-0.02em' }}>
                  ระบบวิเคราะห์ข้อมูลจราจรเชิงธุรกิจ (Business Intelligence Portal)
                </h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  เชื่อมต่อสถิติการจราจรเข้ากับเป้าหมายทางธุรกิจ (ยอดลูกค้าเข้าร้าน, Peak Hours, ประมาณการ Footfall)
                </p>
              </div>
            </div>
          </div>

          {/* Action buttons to add custom data */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => { setFormMsg(null); setShowAddBizModal(true); }}
              className="btn btn-primary"
              style={{
                padding: '10px 18px',
                fontSize: '0.85rem',
                fontWeight: '700',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>➕</span>
              <span>เพิ่มสาขา / องค์กรธุรกิจใหม่</span>
            </button>

            <button
              type="button"
              onClick={() => { setFormMsg(null); setShowAddCamModal(true); }}
              className="btn btn-secondary"
              disabled={!selectedBizId}
              style={{
                padding: '10px 18px',
                fontSize: '0.85rem',
                fontWeight: '700',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>📹</span>
              <span>เพิ่มกล้อง CCTV ประจำสาขา</span>
            </button>
          </div>
        </div>

        {/* Filter controls row */}
        <div style={{
          marginTop: '20px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          {/* Business Branch Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
              เลือกสาขา / ธุรกิจ:
            </label>
            <select
              value={selectedBizId || ''}
              onChange={(e) => setSelectedBizId(Number(e.target.value))}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                background: 'var(--bg-input)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.85rem',
                fontWeight: '700'
              }}
            >
              {businesses.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.branch_code || 'Main'}) - {b.cameras_count || 0} กล้อง
                </option>
              ))}
            </select>
          </div>

          {/* Date filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
              วันที่วิเคราะห์:
            </label>
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                background: 'var(--bg-input)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.85rem',
                fontWeight: '600'
              }}
            >
              <option value="">ทั้งหมด (All-Time Data)</option>
              {dates.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 2. Key Business Metrics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        {/* KPI 1: Customer Traffic */}
        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #3b82f6' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#60a5fa', textTransform: 'uppercase' }}>
            ยอดรถลูกค้าเข้าร้าน / สาขา (Total Traffic)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', marginTop: '6px' }}>
            {kpis.total_vehicles?.toLocaleString() || 0} <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>คัน</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            ในช่วงเวลาเปิดทำการ: {kpis.operating_hours_traffic?.toLocaleString() || 0} คัน
          </div>
        </div>

        {/* KPI 2: Estimated Footfall */}
        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#34d399', textTransform: 'uppercase' }}>
            ประมาณการจำนวนผู้มาเยือน (Estimated Footfall)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', marginTop: '6px', color: '#10b981' }}>
            ~{kpis.estimated_footfall?.toLocaleString() || 0} <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>คน</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            คำนวณจากประเภทและสัดส่วนผู้โดยสารในรถ
          </div>
        </div>

        {/* KPI 3: Peak Customer Arrival Hour */}
        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#fbbf24', textTransform: 'uppercase' }}>
            ช่วงเวลาลูกค้าหนาแน่นที่สุด (Peak Business Hour)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', marginTop: '6px' }}>
            {kpis.peak_hour || '--:--'}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            เฉลี่ยสูงสุด {kpis.peak_vehicle_count || 0} คัน/ชั่วโมง (เหมาะจัดกะพนักงาน)
          </div>
        </div>

        {/* KPI 4: Target Achievement */}
        <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #8b5cf6' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#a78bfa', textTransform: 'uppercase' }}>
            อัตราความหนาแน่นเทียบเป้าหมาย (Target Ratio)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', marginTop: '6px' }}>
            {kpis.target_achievement_pct || 0}%
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            เป้าหมาย: {kpis.target_hourly_traffic || 100} คัน/ชม. (จริง {kpis.avg_hourly_traffic || 0})
          </div>
        </div>
      </div>

      {/* 3. Customer Traffic by Operating Hours (Hourly Inflow SVG Chart) */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📊</span>
              <span>พฤติกรรมการเข้ามาของลูกค้าในแต่ละชั่วโมง (Customer Inflow Distribution)</span>
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              เวลาเปิด-ปิดสาขา: {currentBiz.opening_hour || 8}:00 น. - {currentBiz.closing_hour || 22}:00 น.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'var(--accent-primary)' }} />
              <span>เวลาเปิดทำการ</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#f59e0b' }} />
              <span>ชั่วโมงพีคสูงสุด (Peak)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'rgba(255,255,255,0.1)' }} />
              <span>นอกเวลาทำการ</span>
            </div>
          </div>
        </div>

        {/* SVG Bar Chart */}
        <div style={{ overflowX: 'auto', paddingBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', height: '180px', gap: '6px', minWidth: '700px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            {hourly.map((h) => {
              const heightPct = Math.max(4, (h.total / maxHourlyTraffic) * 100);
              const isPeak = h.hour_label.startsWith(kpis.peak_hour?.substring(0, 2) || '');

              let barColor = 'rgba(255, 255, 255, 0.12)';
              if (isPeak) {
                barColor = 'linear-gradient(180deg, #f59e0b, #d97706)';
              } else if (h.is_operating_hour) {
                barColor = 'linear-gradient(180deg, #3b82f6, #1d4ed8)';
              }

              return (
                <div
                  key={h.hour}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    height: '100%',
                    justifyContent: 'flex-end',
                    position: 'relative'
                  }}
                  title={`${h.hour_label}: ${h.total} คัน (เข้า: ${h.inbound}, ออก: ${h.outbound})`}
                >
                  {h.total > 0 && (
                    <span style={{ fontSize: '0.65rem', fontWeight: '700', marginBottom: '4px', color: isPeak ? '#f59e0b' : 'var(--text-secondary)' }}>
                      {h.total}
                    </span>
                  )}
                  <div
                    style={{
                      width: '100%',
                      height: `${heightPct}%`,
                      background: barColor,
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.4s ease'
                    }}
                  />
                  <span style={{ fontSize: '0.68rem', color: h.is_operating_hour ? 'var(--text-primary)' : 'var(--text-muted)', marginTop: '8px', fontWeight: isPeak ? '800' : '500' }}>
                    {h.hour}น.
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. Branch CCTV Cameras Management */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📹</span>
              <span>กล้องวงจรปิด CCTV ที่เชื่อมต่อกับสาขานี้ ({analytics?.cameras?.length || 0} กล้อง)</span>
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              สามารถผูก URL สตรีมกล้อง CCTV / RTSP ของสาขาเพื่อวิเคราะห์ข้อมูลแบบสดๆ
            </p>
          </div>

          <button
            type="button"
            onClick={() => { setFormMsg(null); setShowAddCamModal(true); }}
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem', padding: '8px 14px', borderRadius: '8px', fontWeight: '700' }}
          >
            ➕ เพิ่มกล้องใหม่
          </button>
        </div>

        {analytics?.cameras?.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px 14px' }}>ชื่อกล้อง</th>
                  <th style={{ padding: '10px 14px' }}>ประเภทจุดตรวจจับ</th>
                  <th style={{ padding: '10px 14px' }}>URL สัญญาณสตรีม</th>
                  <th style={{ padding: '10px 14px' }}>ตำแหน่ง / หมายเหตุ</th>
                  <th style={{ padding: '10px 14px', textAlign: 'center' }}>การดำเนินการ</th>
                </tr>
              </thead>
              <tbody>
                {analytics.cameras.map((c) => (
                  <tr key={c.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '12px 14px', fontWeight: '700' }}>{c.name}</td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontSize: '0.72rem',
                        fontWeight: '700',
                        background: c.camera_type === 'entrance' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                        color: c.camera_type === 'entrance' ? '#10b981' : '#60a5fa'
                      }}>
                        {c.camera_type === 'entrance' ? '🚪 ทางเข้า (Entrance)' :
                         c.camera_type === 'exit' ? '🚗 ทางออก (Exit)' :
                         c.camera_type === 'parking' ? '🅿️ ลานจอด (Parking)' : '🛣️ ช่องจราจร'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {c.stream_url}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>
                      {c.location_note || '-'}
                    </td>
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <button
                        type="button"
                        onClick={() => handleDeleteCamera(c.id)}
                        className="btn btn-danger"
                        style={{ padding: '4px 10px', fontSize: '0.72rem', borderRadius: '6px' }}
                      >
                        🗑️ ลบ
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
            ยังไม่มีการผูกกล้อง CCTV กับสาขานี้ กดปุ่ม <b>"เพิ่มกล้อง CCTV ประจำสาขา"</b> เพื่อกรอกข้อมูลกล้องของคุณได้เลยครับ
          </div>
        )}
      </div>

      {/* MODAL: ADD BUSINESS */}
      {showAddBizModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '16px'
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: '520px', padding: '28px', borderRadius: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800' }}>🏢 เพิ่มสาขา / องค์กรธุรกิจใหม่</h3>
              <button type="button" onClick={() => setShowAddBizModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            {formMsg && (
              <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontSize: '0.85rem', marginBottom: '16px' }}>
                ⚠️ {formMsg}
              </div>
            )}

            <form onSubmit={handleCreateBusiness} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>ชื่อสาขา / องค์กรธุรกิจ *</label>
                <input
                  type="text" required placeholder="เช่น เซ็นทรัล ศรีราชา หรือ ปั๊ม ปตท. มอเตอร์เวย์"
                  value={newBiz.name} onChange={(e) => setNewBiz({ ...newBiz, name: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>ประเภทธุรกิจ</label>
                  <select
                    value={newBiz.business_type} onChange={(e) => setNewBiz({ ...newBiz, business_type: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                  >
                    <option value="retail">🛍️ ห้าง / ร้านค้าปลีก (Retail)</option>
                    <option value="gas_station">⛽ ปั๊มน้ำมัน / EV Hub</option>
                    <option value="logistics">🚛 ศูนย์กระจายสินค้า (Logistics)</option>
                    <option value="smart_parking">🅿️ อาคารจอดรถอัจฉริยะ</option>
                    <option value="campus">🏫 สถานศึกษา / มหาวิทยาลัย</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>รหัสสาขา (Branch Code)</label>
                  <input
                    type="text" placeholder="BKK-01"
                    value={newBiz.branch_code} onChange={(e) => setNewBiz({ ...newBiz, branch_code: e.target.value })}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', marginBottom: '4px' }}>เวลาเปิด (น.)</label>
                  <input
                    type="number" min="0" max="23" value={newBiz.opening_hour}
                    onChange={(e) => setNewBiz({ ...newBiz, opening_hour: Number(e.target.value) })}
                    style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', marginBottom: '4px' }}>เวลาปิด (น.)</label>
                  <input
                    type="number" min="0" max="23" value={newBiz.closing_hour}
                    onChange={(e) => setNewBiz({ ...newBiz, closing_hour: Number(e.target.value) })}
                    style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', marginBottom: '4px' }}>เป้าหมาย (คัน/ชม.)</label>
                  <input
                    type="number" min="1" value={newBiz.target_hourly_traffic}
                    onChange={(e) => setNewBiz({ ...newBiz, target_hourly_traffic: Number(e.target.value) })}
                    style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>ที่อยู่ / ทำเลที่ตั้ง</label>
                <input
                  type="text" placeholder="เช่น อ.ศรีราชา จ.ชลบุรี"
                  value={newBiz.address} onChange={(e) => setNewBiz({ ...newBiz, address: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ padding: '12px', borderRadius: '10px', fontWeight: '800', marginTop: '6px' }}>
                💾 บันทึกข้อมูลธุรกิจ
              </button>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD CAMERA */}
      {showAddCamModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '16px'
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: '500px', padding: '28px', borderRadius: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800' }}>📹 เพิ่มกล้อง CCTV ประจำสาขา</h3>
              <button type="button" onClick={() => setShowAddCamModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            {formMsg && (
              <div style={{ padding: '10px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontSize: '0.85rem', marginBottom: '16px' }}>
                ⚠️ {formMsg}
              </div>
            )}

            <form onSubmit={handleCreateCamera} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>ชื่อกล้อง *</label>
                <input
                  type="text" required placeholder="เช่น กล้องทางเข้าหลัก Gate 1"
                  value={newCam.name} onChange={(e) => setNewCam({ ...newCam, name: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>URL สตรีมกล้อง (RTSP / HTTP / HLS) *</label>
                <input
                  type="text" required placeholder="rtsp://admin:pass@192.168.1.100:554/stream1 หรือ http://..."
                  value={newCam.stream_url} onChange={(e) => setNewCam({ ...newCam, stream_url: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>ประเภทจุดตรวจจับ</label>
                <select
                  value={newCam.camera_type} onChange={(e) => setNewCam({ ...newCam, camera_type: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                >
                  <option value="entrance">🚪 ทางเข้า (Entrance - นับรถเข้า)</option>
                  <option value="exit">🚗 ทางออก (Exit - นับรถออก)</option>
                  <option value="parking">🅿️ ลานจอดรถ (Parking Bay)</option>
                  <option value="lane">🛣️ ช่องจราจร / ถนนหน้าสาขา</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '4px' }}>หมายเหตุตำแหน่ง</label>
                <input
                  type="text" placeholder="เช่น ติดตั้งเหนือเสาไฟหน้าป้อมยาม"
                  value={newCam.location_note} onChange={(e) => setNewCam({ ...newCam, location_note: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: '#fff' }}
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ padding: '12px', borderRadius: '10px', fontWeight: '800', marginTop: '6px' }}>
                💾 บันทึกกล้อง CCTV
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
