import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function ControlPanel({
  config,
  onChangeConfig,
  onUploadSuccess,
  onToggleCalibrationPreview,
  showCalibration,
  modelStatus,
  testCctv,
  cctvTestResult,
  setCctvTestResult
}) {
  const [videos, setVideos] = useState([]);
  const [models, setModels] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isTestingCctv, setIsTestingCctv] = useState(false);
  const [showCctvHelp, setShowCctvHelp] = useState(false);
  const [cctvUrlInput, setCctvUrlInput] = useState('');

  useEffect(() => {
    if (config.video_path && config.video_path !== 'rtsp_stream') {
      setCctvUrlInput(config.video_path);
    }
  }, [config.video_path]);

  useEffect(() => {
    if (cctvTestResult) {
      setIsTestingCctv(false);
    }
  }, [cctvTestResult]);

  useEffect(() => {
    async function loadResources() {
      try {
        const vidData = await api.getVideos();
        if (vidData && vidData.videos && vidData.videos.length > 0) {
          setVideos(vidData.videos);
          // If current video_path is empty or not in videos, select first available video
          const exists = vidData.videos.some((v) => v.path === config.video_path);
          if (!exists) {
            onChangeConfig('video_path', vidData.videos[0].path);
          }
        }
        const modelData = await api.getModels();
        if (modelData && modelData.models && modelData.models.length > 0) {
          setModels(modelData.models);
          if (!config.model_name) {
            onChangeConfig('model_name', modelData.models[0].name);
          }
        }
      } catch (err) {
        console.error('Failed to load initial resources', err);
      }
    }
    loadResources();
  }, []);


  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const res = await api.uploadVideo(file);
      if (res.video) {
        setVideos((prev) => [res.video, ...prev]);
        onChangeConfig('video_path', res.video.path);
        if (onUploadSuccess) onUploadSuccess(res.video);
      }
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClassToggle = (className) => {
    const current = config.target_classes || ['Car', 'Motorcycle', 'Bus', 'Truck'];
    const updated = current.includes(className)
      ? current.filter((c) => c !== className)
      : [...current, className];
    onChangeConfig('target_classes', updated);
  };

  return (
    <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <h3 style={{ fontSize: '1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
        ⚙️ Control Panel & Calibration
      </h3>

      {/* Video Source Selection */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
            📹 Video Source / Camera Feed
          </label>
          {(config.video_path === 'webcam:0' || config.video_path?.startsWith('rtsp://') || config.video_path?.startsWith('http://')) && (
            <span style={{ fontSize: '0.75rem', color: '#10B981', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10B981', display: 'inline-block' }}></span>
              REAL-TIME LIVE
            </span>
          )}
        </div>

        <select
          className="form-select"
          value={config.video_path || ''}
          onChange={(e) => {
            const val = e.target.value;
            onChangeConfig('video_path', val);
          }}
        >
          {videos.map((v) => (
            <option key={v.id} value={v.path}>
              {v.name}
            </option>
          ))}
        </select>

        {/* Live Camera Indicators */}
        {config.video_path === 'webcam:0' && (
          <div style={{ marginTop: '8px', padding: '8px 12px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', fontSize: '0.75rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1rem' }}>📷</span>
            <div>
              <strong>กล้องเว็บแคมสด (Direct Camera 0):</strong> ประมวลผลภาพสดแบบเรียลไทม์ไม่มีดีเลย์
            </div>
          </div>
        )}

        {/* Custom RTSP / IP Camera Input */}
        {(config.video_path === 'rtsp_stream' || config.video_path?.startsWith('rtsp://') || config.video_path?.startsWith('http://') || config.video_path?.startsWith('https://')) && (
          <div style={{ marginTop: '8px', padding: '12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--accent-primary)', display: 'block' }}>
                🌐 ระบุ URL กล้องวงจรปิด (RTSP / HTTP IP Camera)
              </label>
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                type="text"
                className="form-input"
                placeholder="rtsp://admin:pass@192.168.1.100:554/stream1"
                value={cctvUrlInput}
                onChange={(e) => {
                  setCctvUrlInput(e.target.value);
                  onChangeConfig('video_path', e.target.value.trim());
                  if (setCctvTestResult) setCctvTestResult(null);
                }}
                style={{ flex: 1, fontSize: '0.8rem', padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)' }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                disabled={isTestingCctv || !cctvUrlInput.trim() || cctvUrlInput === 'rtsp_stream'}
                onClick={() => {
                  if (testCctv && cctvUrlInput.trim()) {
                    setIsTestingCctv(true);
                    testCctv(cctvUrlInput.trim());
                  }
                }}
                style={{ fontSize: '0.75rem', padding: '8px 12px', whiteSpace: 'nowrap', minWidth: '100px' }}
              >
                {isTestingCctv ? '⏳ กำลังทดสอบ...' : '⚡ ทดสอบสัญญาณ'}
              </button>
            </div>

            {/* Test Result Message */}
            {cctvTestResult && (
              <div style={{
                marginTop: '8px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                backgroundColor: cctvTestResult.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: cctvTestResult.success ? '#10B981' : '#EF4444',
                border: `1px solid ${cctvTestResult.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                {cctvTestResult.message}
              </div>
            )}

            {/* Quick Brand Presets */}
            <div style={{ marginTop: '10px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                คลิกเพื่อใส่ตัวอย่างตามยี่ห้อกล้อง:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.65rem', padding: '3px 8px' }}
                  onClick={() => {
                    const sample = 'http://192.168.1.100:8080/video';
                    setCctvUrlInput(sample);
                    onChangeConfig('video_path', sample);
                  }}
                >
                  📱 มือถือ IP Webcam
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.65rem', padding: '3px 8px' }}
                  onClick={() => {
                    const sample = 'rtsp://admin:12345@192.168.1.100:554/stream1';
                    setCctvUrlInput(sample);
                    onChangeConfig('video_path', sample);
                  }}
                >
                  📹 Tapo / TP-Link
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.65rem', padding: '3px 8px' }}
                  onClick={() => {
                    const sample = 'rtsp://admin:12345@192.168.1.100:554/Streaming/Channels/101';
                    setCctvUrlInput(sample);
                    onChangeConfig('video_path', sample);
                  }}
                >
                  📹 Hikvision
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.65rem', padding: '3px 8px' }}
                  onClick={() => {
                    const sample = 'rtsp://admin:12345@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0';
                    setCctvUrlInput(sample);
                    onChangeConfig('video_path', sample);
                  }}
                >
                  📹 Dahua / IMOU
                </button>
              </div>
            </div>

            {/* Collapsible CCTV Help */}
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => setShowCctvHelp(!showCctvHelp)}
                style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontSize: '0.75rem', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
              >
                {showCctvHelp ? '▲ ซ่อนคู่มือตั้งค่ากล้องวงจรปิด' : '▼ วิธีเชื่อมต่อกล้อง CCTV / มือถือกล้องสด'}
              </button>
              {showCctvHelp && (
                <div style={{ marginTop: '6px', padding: '10px', background: 'rgba(0,0,0,0.25)', borderRadius: '6px', fontSize: '0.72rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                  <div><strong>1. ใช้มือถือเป็นกล้อง CCTV (แนะนำสำหรับทดสอบ):</strong></div>
                  <div>- โหลดแอป <strong>"IP Webcam"</strong> (Android) หรือ <strong>"Live-Reporter"</strong> (iOS)</div>
                  <div>- กดเปิดเซิร์ฟเวอร์ในแอป จะได้ URL เช่น <code>http://192.168.1.X:8080/video</code> มาวางที่นี่</div>
                  <div style={{ marginTop: '6px' }}><strong>2. กล้องวงจรปิดจริง (CCTV / NVR):</strong></div>
                  <div>- ต้องเปิดบริการ RTSP ในตั้งค่าของกล้อง (เช่น Tapo ให้เข้าไปสร้าง Camera Account ก่อน)</div>
                  <div>- คอมพิวเตอร์และกล้องต้องต่อเราเตอร์ Wi-Fi หรือวง LAN เดียวกัน</div>
                  <div>- ต้องใส่ Username/Password ของกล้องใน URL เสมอ เช่น <code>rtsp://user:pass@ip:554/...</code></div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Upload Button */}
        <div style={{ marginTop: '8px' }}>
          <label className="btn btn-secondary" style={{ width: '100%', cursor: 'pointer', fontSize: '0.8rem' }}>
            {isUploading ? '⏳ Uploading...' : '📁 หรืออัปโหลดไฟล์วิดีโอ (.mp4 / .mov)'}
            <input type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFileUpload} disabled={isUploading} />
          </label>
        </div>
      </div>

      {/* YOLO Model Selection */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
            🤖 YOLO AI Model
          </label>
          {modelStatus?.status === 'loading' && (
            <span style={{ fontSize: '0.75rem', color: '#F59E0B', fontWeight: '600' }}>
              ⏳ Loading {modelStatus.model}...
            </span>
          )}
        </div>
        <select
          className="form-select"
          disabled={modelStatus?.status === 'loading'}
          value={config.model_name || 'best.pt'}
          onChange={(e) => onChangeConfig('model_name', e.target.value)}
        >
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      {/* Confidence Threshold */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
          <span style={{ color: 'var(--text-secondary)' }}>🎯 Confidence Threshold</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)' }}>
            {(config.conf_threshold * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0.10"
          max="0.90"
          step="0.05"
          value={config.conf_threshold || 0.25}
          onChange={(e) => onChangeConfig('conf_threshold', parseFloat(e.target.value))}
        />
      </div>

      <hr style={{ borderColor: 'var(--border-color)', margin: '4px 0' }} />

      {/* Tripwire Calibration Section */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: '700' }}>📐 Tripwire Calibration</span>
          <button
            onClick={onToggleCalibrationPreview}
            className={`btn ${showCalibration ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
          >
            {showCalibration ? '👁️ Hide Preview' : '📐 Adjust Lines'}
          </button>
        </div>

        {/* Line Y Slider */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Tripwire Y-Position</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{((config.line_y_ratio || 0.5) * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.20"
            max="0.85"
            step="0.01"
            value={config.line_y_ratio || 0.50}
            onChange={(e) => onChangeConfig('line_y_ratio', parseFloat(e.target.value))}
          />
        </div>

        {/* Divider Mid X Slider */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Median Divider X</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{((config.mid_x_ratio || 0.45) * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.20"
            max="0.80"
            step="0.01"
            value={config.mid_x_ratio || 0.45}
            onChange={(e) => onChangeConfig('mid_x_ratio', parseFloat(e.target.value))}
          />
        </div>

        {/* Direction Swap Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Swap In/Out Directions</span>
          <input
            type="checkbox"
            checked={config.swap_directions || false}
            onChange={(e) => onChangeConfig('swap_directions', e.target.checked)}
            style={{ width: '18px', height: '18px', accentColor: 'var(--accent-primary)', cursor: 'pointer' }}
          />
        </div>
      </div>

      <hr style={{ borderColor: 'var(--border-color)', margin: '4px 0' }} />

      {/* Target Classes Filter */}
      <div>
        <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
          🚗 Target Vehicle Classes
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {['Car', 'Motorcycle', 'Bus', 'Truck'].map((cls) => {
            const isChecked = (config.target_classes || ['Car', 'Motorcycle', 'Bus', 'Truck']).includes(cls);
            return (
              <label
                key={cls}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '0.8rem',
                  padding: '6px 10px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-input)',
                  border: `1px solid ${isChecked ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleClassToggle(cls)}
                  style={{ accentColor: 'var(--accent-primary)' }}
                />
                <span>{cls}</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}
