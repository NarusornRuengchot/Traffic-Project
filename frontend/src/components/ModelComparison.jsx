import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function ModelComparison({ currentSource = 'IMG_1357.MOV', onSelectModel, onSwitchToLive }) {
  const [selectedSource, setSelectedSource] = useState(currentSource);
  const [customRtspUrl, setCustomRtspUrl] = useState('');
  const [sampleFrames, setSampleFrames] = useState(10);
  const [confThreshold, setConfThreshold] = useState(0.18);
  const [selectedModels, setSelectedModels] = useState([
    'best.pt',
    'yolo26s.pt',
    'yolo26n.pt',
    'yolov11n.pt'
  ]);
  const [availableModels, setAvailableModels] = useState([]);
  const [presets, setPresets] = useState([]);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);

  // Side-by-side visual comparison model selection
  const [compareModelA, setCompareModelA] = useState('best.pt');
  const [compareModelB, setCompareModelB] = useState('yolo26s.pt');

  // Load presets & models on mount
  useEffect(() => {
    async function init() {
      try {
        const data = await api.getBenchmarkPresets();
        if (data) {
          if (data.presets) setPresets(data.presets);
          if (data.available_models) {
            setAvailableModels(data.available_models);
          }
        }
      } catch (err) {
        console.error('Failed to load benchmark presets', err);
      }
    }
    init();
  }, []);

  const handleToggleModel = (mName) => {
    setSelectedModels((prev) => {
      if (prev.includes(mName)) {
        if (prev.length <= 1) return prev; // Keep at least one
        return prev.filter((m) => m !== mName);
      } else {
        return [...prev, mName];
      }
    });
  };

  const handleRunBenchmark = async () => {
    setIsRunning(true);
    setError(null);
    const videoSource = selectedSource === 'custom_rtsp' ? customRtspUrl.trim() : selectedSource;

    if (selectedSource === 'custom_rtsp' && !customRtspUrl.trim()) {
      setError('กรุณากรอก URL กล้อง CCTV / RTSP ก่อนกดเริ่มทดสอบ');
      setIsRunning(false);
      return;
    }

    try {
      const res = await api.runBenchmark({
        video_source: videoSource,
        models: selectedModels,
        sample_frames: sampleFrames,
        conf_threshold: confThreshold
      });

      setBenchmarkData(res);
      if (res && res.results && res.results.length >= 2) {
        setCompareModelA(res.results[0].model_name);
        setCompareModelB(res.results[1].model_name);
      }
    } catch (err) {
      setError(err.message || 'เกิดข้อผิดพลาดในการประเมินโมเดล');
    } finally {
      setIsRunning(false);
    }
  };

  const handleApplyModel = (modelName) => {
    if (onSelectModel) {
      onSelectModel(modelName);
    }
    if (onSwitchToLive) {
      onSwitchToLive();
    }
  };

  // Find preview images for side-by-side
  const resultA = benchmarkData?.results?.find((r) => r.model_name === compareModelA);
  const resultB = benchmarkData?.results?.find((r) => r.model_name === compareModelB);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. Header & Configuration Glass Card */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>⚖️</span>
              <span>เชื่อมต่อ CCTV และเปรียบเทียบความแม่นยำ AI (Model Benchmark)</span>
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              ทดสอบและประเมินประสิทธิภาพระหว่างโมเดล AI แต่ละตัวบนเฟรมกล้อง CCTV เดียวกันแบบ Real-time
            </p>
          </div>

          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={isRunning || selectedModels.length === 0}
            style={{
              padding: '12px 28px',
              borderRadius: '12px',
              fontSize: '0.95rem',
              fontWeight: '800',
              border: 'none',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              background: isRunning ? 'var(--bg-input)' : 'linear-gradient(135deg, #2563eb, #06b6d4)',
              color: '#fff',
              boxShadow: isRunning ? 'none' : '0 4px 16px rgba(37, 99, 235, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            {isRunning ? (
              <>
                <span className="spinner" style={{ width: '18px', height: '18px' }} />
                <span>กำลังประมวลผลเปรียบเทียบ AI...</span>
              </>
            ) : (
              <>
                <span>🚀</span>
                <span>เริ่มประเมินความแม่นยำ (Run Benchmark)</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div style={{
            padding: '12px 16px',
            borderRadius: '10px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#ef4444',
            fontSize: '0.88rem',
            marginBottom: '16px'
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Input Controls Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px' }}>
          {/* CCTV Source Preset */}
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              📹 แหล่งสัญญาณภาพ (CCTV / Video Stream)
            </label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '10px',
                background: 'var(--bg-input)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.88rem',
                fontWeight: '600'
              }}
            >
              <option value="IMG_1357.MOV">🏫 KUSRC Campus CCTV (จำลองกล้องวงจรปิด มก.ศรีราชา)</option>
              <option value="webcam:0">💻 Local Webcam สด (webcam:0)</option>
              <option value="custom_rtsp">🌐 Custom RTSP / IP Camera (ระบุ URL เอง)</option>
            </select>

            {selectedSource === 'custom_rtsp' && (
              <input
                type="text"
                placeholder="rtsp://admin:pass@192.168.1.100:554/stream1"
                value={customRtspUrl}
                onChange={(e) => setCustomRtspUrl(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '8px',
                  padding: '9px 12px',
                  borderRadius: '8px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              />
            )}
          </div>

          {/* Sample Frames Count */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <label style={{ fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
                🎞️ จำนวนเฟรมที่สุ่มทดสอบ (Sample Frames)
              </label>
              <span style={{ fontSize: '0.82rem', fontWeight: '800', color: 'var(--accent-primary)' }}>
                {sampleFrames} เฟรม
              </span>
            </div>
            <input
              type="range"
              min="5"
              max="25"
              step="1"
              value={sampleFrames}
              onChange={(e) => setSampleFrames(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              <span>5 เฟรม (รวดเร็ว)</span>
              <span>15 เฟรม (มาตรฐาน)</span>
              <span>25 เฟรม (ละเอียดสูง)</span>
            </div>
          </div>

          {/* Confidence Threshold */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <label style={{ fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
                🎯 เกณฑ์ความเชื่อมั่น (Confidence Threshold)
              </label>
              <span style={{ fontSize: '0.82rem', fontWeight: '800', color: '#10b981' }}>
                {Math.round(confThreshold * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.60"
              step="0.02"
              value={confThreshold}
              onChange={(e) => setConfThreshold(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#10b981' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              <span>10% (ตรวจจับไว)</span>
              <span>25% (มาตรฐาน)</span>
              <span>60% (เข้มงวด)</span>
            </div>
          </div>
        </div>

        {/* Model Selection Checkbox Pills */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '10px' }}>
            🧠 เลือกโมเดลที่ต้องการนำมาเปรียบเทียบ (เลือกอย่างน้อย 1 ตัว)
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {[
              { id: 'best.pt', label: 'best.pt', desc: 'Custom Fine-Tuned (ไทย)' },
              { id: 'best_finetuned_50f.pt', label: 'best_finetuned_50f.pt', desc: 'Fine-Tuned 50f' },
              { id: 'yolo26s.pt', label: 'yolo26s.pt', desc: 'YOLO26 Small' },
              { id: 'yolo26n.pt', label: 'yolo26n.pt', desc: 'YOLO26 Nano (เร็วสุด)' },
              { id: 'yolov11n.pt', label: 'yolov11n.pt', desc: 'YOLO11 Baseline' }
            ].map((m) => {
              const active = selectedModels.includes(m.id);
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleToggleModel(m.id)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '10px',
                    border: active ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                    background: active ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-input)',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '4px',
                    border: active ? 'none' : '1px solid var(--border-color)',
                    background: active ? 'var(--accent-primary)' : 'transparent',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '11px',
                    color: '#fff'
                  }}>
                    {active ? '✓' : ''}
                  </span>
                  <span>{m.label}</span>
                  <span style={{ fontSize: '0.72rem', opacity: 0.7, fontWeight: '400' }}>({m.desc})</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 2. Benchmark Results Area */}
      {benchmarkData && (
        <>
          {/* Winner Badges Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            {/* Accuracy Winner */}
            <div className="glass-card" style={{ padding: '18px 20px', borderLeft: '4px solid #10b981' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '24px' }}>🏆</span>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#10b981', textTransform: 'uppercase' }}>
                    ความแม่นยำสูงสุด (Highest Accuracy)
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: '800' }}>
                    {benchmarkData.winners?.accuracy_winner || '--'}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                ให้ค่า Mean Confidence Score สูงสุดบนสตรีมกล้อง CCTV นี้
              </p>
            </div>

            {/* Speed Winner */}
            <div className="glass-card" style={{ padding: '18px 20px', borderLeft: '4px solid #3b82f6' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '24px' }}>⚡</span>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#3b82f6', textTransform: 'uppercase' }}>
                    ประมวลผลเร็วที่สุด (Fastest FPS)
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: '800' }}>
                    {benchmarkData.winners?.speed_winner || '--'}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Latency ต่ำสุด กินทรัพยากรน้อย เหมาะกับการรัน Real-time
              </p>
            </div>

            {/* Motorcycle Winner */}
            <div className="glass-card" style={{ padding: '18px 20px', borderLeft: '4px solid #f59e0b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '24px' }}>🛵</span>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#f59e0b', textTransform: 'uppercase' }}>
                    จับมอเตอร์ไซค์ดีที่สุด (Best Motorcycle AI)
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: '800' }}>
                    {benchmarkData.winners?.motorcycle_winner || '--'}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                ตรวจจับรถจักรยานยนต์ในไทยได้ครบถ้วนและแม่นยำที่สุด
              </p>
            </div>

            {/* Balanced Recommendation */}
            <div className="glass-card" style={{ padding: '18px 20px', borderLeft: '4px solid #8b5cf6' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '24px' }}>🎯</span>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#8b5cf6', textTransform: 'uppercase' }}>
                    โมเดลที่แนะนำ (Recommended)
                  </div>
                  <div style={{ fontSize: '1.15rem', fontWeight: '800' }}>
                    {benchmarkData.winners?.recommended_model || '--'}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                จุดสมดุลที่ดีที่สุดระหว่างความเร็วและความแม่นยำ
              </p>
            </div>
          </div>

          {/* 3. Side-by-Side Visual Inspection */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>📸</span>
                  <span>เปรียบเทียบภาพ Bounding Box สดแบบ Side-by-Side</span>
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  แสดงผลลัพธ์การตีกรอบยานพาหนะและค่าความมั่นใจบนเฟรม CCTV เดียวกันเปรียบเทียบแบบจะๆ
                </p>
              </div>

              {/* Selector for Model A and B */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <select
                  value={compareModelA}
                  onChange={(e) => setCompareModelA(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.82rem',
                    fontWeight: '700'
                  }}
                >
                  {benchmarkData.results.map((r) => (
                    <option key={`a-${r.model_name}`} value={r.model_name}>
                      โมเดล 1: {r.model_name}
                    </option>
                  ))}
                </select>

                <span style={{ fontWeight: '800', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>VS</span>

                <select
                  value={compareModelB}
                  onChange={(e) => setCompareModelB(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.82rem',
                    fontWeight: '700'
                  }}
                >
                  {benchmarkData.results.map((r) => (
                    <option key={`b-${r.model_name}`} value={r.model_name}>
                      โมเดล 2: {r.model_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
              {/* Box A */}
              <div style={{ background: 'var(--bg-card)', borderRadius: '12px', padding: '14px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontWeight: '800', fontSize: '0.95rem', color: '#60a5fa' }}>
                    {resultA?.model_name || compareModelA}
                  </span>
                  <span style={{ fontSize: '0.78rem', background: 'rgba(96, 165, 250, 0.15)', color: '#60a5fa', padding: '2px 8px', borderRadius: '6px' }}>
                    ความมั่นใจ {resultA?.mean_confidence || 0}% | {resultA?.avg_inference_ms || 0} ms
                  </span>
                </div>
                {resultA?.annotated_preview ? (
                  <img
                    src={`data:image/jpeg;base64,${resultA.annotated_preview}`}
                    alt={`Preview ${compareModelA}`}
                    style={{ width: '100%', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'block' }}
                  />
                ) : (
                  <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    ไม่มีภาพตัวอย่าง
                  </div>
                )}
              </div>

              {/* Box B */}
              <div style={{ background: 'var(--bg-card)', borderRadius: '12px', padding: '14px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontWeight: '800', fontSize: '0.95rem', color: '#34d399' }}>
                    {resultB?.model_name || compareModelB}
                  </span>
                  <span style={{ fontSize: '0.78rem', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: '6px' }}>
                    ความมั่นใจ {resultB?.mean_confidence || 0}% | {resultB?.avg_inference_ms || 0} ms
                  </span>
                </div>
                {resultB?.annotated_preview ? (
                  <img
                    src={`data:image/jpeg;base64,${resultB.annotated_preview}`}
                    alt={`Preview ${compareModelB}`}
                    style={{ width: '100%', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'block' }}
                  />
                ) : (
                  <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    ไม่มีภาพตัวอย่าง
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 4. Comparison Charts Area */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px' }}>
            {/* Chart 1: Mean Confidence Comparison */}
            <div className="glass-card" style={{ padding: '22px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📊</span>
                <span>เปรียบเทียบค่าความมั่นใจเฉลี่ย (Mean Confidence Score %)</span>
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {benchmarkData.results.map((r) => {
                  const pct = r.mean_confidence || 0;
                  const isTop = r.model_name === benchmarkData.winners?.accuracy_winner;
                  return (
                    <div key={`conf-${r.model_name}`}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', fontWeight: '700', marginBottom: '4px' }}>
                        <span>
                          {r.model_name} {isTop ? '🏆' : ''}
                        </span>
                        <span style={{ color: isTop ? '#10b981' : 'var(--text-primary)' }}>
                          {pct}%
                        </span>
                      </div>
                      <div style={{ height: '10px', background: 'var(--bg-input)', borderRadius: '6px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${pct}%`,
                            background: isTop ? 'linear-gradient(90deg, #10b981, #06b6d4)' : 'linear-gradient(90deg, #3b82f6, #6366f1)',
                            borderRadius: '6px',
                            transition: 'width 0.6s ease'
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Chart 2: Inference Speed (FPS & Latency) */}
            <div className="glass-card" style={{ padding: '22px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>⚡</span>
                <span>ความเร็วประมวลผล (Effective FPS & Latency ms)</span>
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {benchmarkData.results.map((r) => {
                  const fpsVal = r.fps || 0;
                  const maxFps = Math.max(60, ...benchmarkData.results.map((x) => x.fps || 0));
                  const widthPct = Math.min(100, (fpsVal / maxFps) * 100);
                  const isFastest = r.model_name === benchmarkData.winners?.speed_winner;
                  return (
                    <div key={`fps-${r.model_name}`}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', fontWeight: '700', marginBottom: '4px' }}>
                        <span>
                          {r.model_name} {isFastest ? '⚡' : ''}
                        </span>
                        <span style={{ color: isFastest ? '#3b82f6' : 'var(--text-primary)' }}>
                          {fpsVal} FPS ({r.avg_inference_ms} ms)
                        </span>
                      </div>
                      <div style={{ height: '10px', background: 'var(--bg-input)', borderRadius: '6px', overflow: 'hidden' }}>
                        <div
                          style={{
                            height: '100%',
                            width: `${widthPct}%`,
                            background: isFastest ? 'linear-gradient(90deg, #3b82f6, #ec4899)' : 'linear-gradient(90deg, #64748b, #94a3b8)',
                            borderRadius: '6px',
                            transition: 'width 0.6s ease'
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 5. Detailed Benchmark Table */}
          <div className="glass-card" style={{ padding: '22px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📋</span>
              <span>ตารางสรุปผลการเปรียบเทียบ AI Model ทั้งหมด</span>
            </h4>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '12px 14px' }}>โมเดล (Model)</th>
                    <th style={{ padding: '12px 14px' }}>ความมั่นใจเฉลี่ย</th>
                    <th style={{ padding: '12px 14px' }}>ตรวจจับทั้งหมด</th>
                    <th style={{ padding: '12px 14px' }}>มอเตอร์ไซค์ (ไทย)</th>
                    <th style={{ padding: '12px 14px' }}>ความเร็ว (FPS)</th>
                    <th style={{ padding: '12px 14px' }}>Latency</th>
                    <th style={{ padding: '12px 14px' }}>ขนาดไฟล์</th>
                    <th style={{ padding: '12px 14px', textAlign: 'center' }}>การดำเนินการ</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarkData.results.map((r) => {
                    const isAccTop = r.model_name === benchmarkData.winners?.accuracy_winner;
                    const isSpeedTop = r.model_name === benchmarkData.winners?.speed_winner;
                    const isMotorTop = r.model_name === benchmarkData.winners?.motorcycle_winner;

                    return (
                      <tr
                        key={`tbl-${r.model_name}`}
                        style={{
                          borderBottom: '1px solid var(--border-color)',
                          transition: 'background 0.15s ease'
                        }}
                      >
                        <td style={{ padding: '14px', fontWeight: '700' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>{r.model_name}</span>
                            {isAccTop && <span title="แม่นยำสูงสุด">🏆</span>}
                            {isSpeedTop && <span title="เร็วที่สุด">⚡</span>}
                            {isMotorTop && <span title="ตรวจจับมอเตอร์ไซค์ดีที่สุด">🛵</span>}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '400' }}>
                            {r.architecture}
                          </div>
                        </td>

                        <td style={{ padding: '14px' }}>
                          <span style={{ fontWeight: '800', color: isAccTop ? '#10b981' : 'var(--text-primary)' }}>
                            {r.mean_confidence}%
                          </span>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                            ความมั่นใจสูง {r.high_conf_ratio}%
                          </div>
                        </td>

                        <td style={{ padding: '14px' }}>
                          <span style={{ fontWeight: '700' }}>{r.total_detections} คัน</span>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                            ~{r.avg_detections_per_frame} คัน/เฟรม
                          </div>
                        </td>

                        <td style={{ padding: '14px' }}>
                          <span style={{ fontWeight: '700', color: isMotorTop ? '#f59e0b' : 'var(--text-primary)' }}>
                            {r.class_breakdown?.Motorcycle?.count || 0} คัน
                          </span>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                            เฉลี่ย {r.class_breakdown?.Motorcycle?.mean_confidence || 0}%
                          </div>
                        </td>

                        <td style={{ padding: '14px', fontWeight: '700', color: isSpeedTop ? '#3b82f6' : 'var(--text-primary)' }}>
                          {r.fps} FPS
                        </td>

                        <td style={{ padding: '14px', color: 'var(--text-secondary)' }}>
                          {r.avg_inference_ms} ms
                        </td>

                        <td style={{ padding: '14px', color: 'var(--text-secondary)' }}>
                          {r.file_size_mb} MB
                        </td>

                        <td style={{ padding: '14px', textAlign: 'center' }}>
                          <button
                            type="button"
                            onClick={() => handleApplyModel(r.model_name)}
                            style={{
                              padding: '6px 14px',
                              borderRadius: '8px',
                              border: 'none',
                              background: 'rgba(37, 99, 235, 0.15)',
                              color: '#60a5fa',
                              fontSize: '0.78rem',
                              fontWeight: '700',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            ✅ ใช้งานโมเดลนี้
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
