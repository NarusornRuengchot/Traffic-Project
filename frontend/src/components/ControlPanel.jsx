import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function ControlPanel({
  config,
  onChangeConfig,
  onUploadSuccess,
  onToggleCalibrationPreview,
  showCalibration
}) {
  const [videos, setVideos] = useState([]);
  const [models, setModels] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    async function loadResources() {
      try {
        const vidData = await api.getVideos();
        if (vidData && vidData.videos) {
          setVideos(vidData.videos);
        }
        const modelData = await api.getModels();
        if (modelData && modelData.models) {
          setModels(modelData.models);
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
        <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>
          📹 Video Source
        </label>
        <select
          className="form-select"
          value={config.video_path || ''}
          onChange={(e) => onChangeConfig('video_path', e.target.value)}
        >
          {videos.map((v) => (
            <option key={v.id} value={v.path}>
              {v.name}
            </option>
          ))}
        </select>

        {/* Upload Button */}
        <div style={{ marginTop: '8px' }}>
          <label className="btn btn-secondary" style={{ width: '100%', cursor: 'pointer', fontSize: '0.8rem' }}>
            {isUploading ? '⏳ Uploading...' : '📁 Upload Custom Video (.mp4 / .mov)'}
            <input type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFileUpload} disabled={isUploading} />
          </label>
        </div>
      </div>

      {/* YOLO Model Selection */}
      <div>
        <label style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>
          🤖 YOLO AI Model
        </label>
        <select
          className="form-select"
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
