import React, { useRef } from 'react';

export function VideoPlayer({
  currentFrame,
  isPlaying,
  isLive,
  onStart,
  onPause,
  onResume,
  onReset,
  calibrationPreview,
  showCalibration
}) {
  const containerRef = useRef(null);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => alert(err.message));
    } else {
      document.exitFullscreen();
    }
  };

  const displayImage = showCalibration && calibrationPreview ? calibrationPreview : currentFrame;

  return (
    <div className="glass-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
          📹 {isLive ? 'Real-time Live Camera Feed' : 'Live AI Stream & Tracking'}
          {isLive && isPlaying && (
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', fontWeight: '700', border: '1px solid rgba(239, 68, 68, 0.4)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#ef4444', display: 'inline-block' }}></span>
              🔴 LIVE
            </span>
          )}
          {showCalibration && (
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '6px', background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b' }}>
              Calibration Mode
            </span>
          )}
        </h2>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={toggleFullscreen}
            className="btn btn-secondary"
            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
            title="Full Screen"
          >
            ⛶ Expand
          </button>
        </div>
      </div>

      {/* Video Stream Canvas / Frame Container */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16/9',
          backgroundColor: '#000000',
          borderRadius: '12px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'inset 0 0 20px rgba(0,0,0,0.8)'
        }}
      >
        {displayImage ? (
          <img
            src={displayImage}
            alt="AI Traffic Stream"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain'
            }}
          />
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>{isLive ? '📷' : '🎬'}</div>
            <div style={{ fontWeight: '600', fontSize: '1rem', color: 'var(--text-secondary)' }}>
              {isLive ? '🔴 Real-time Live Camera Ready' : 'Stream Ready'}
            </div>
            <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>
              {isLive
                ? 'กดปุ่ม "▶ เริ่มตรวจจับภาพสด (Start Live)" เพื่อเริ่มวิเคราะห์ภาพจากกล้องแบบเรียลไทม์'
                : 'Select a video and press "Start AI Analysis" to begin.'}
            </div>
          </div>
        )}
      </div>

      {/* Control Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          {!isPlaying ? (
            <button onClick={onStart} className="btn btn-primary" style={{ padding: '8px 20px' }}>
              {isLive ? '🔴 ▶ เริ่มตรวจจับภาพสด (Start Live)' : '▶ Start AI Analysis'}
            </button>
          ) : (
            <button onClick={onPause} className="btn btn-secondary" style={{ padding: '8px 20px' }}>
              ⏸ Pause
            </button>
          )}

          <button onClick={onReset} className="btn btn-danger" style={{ padding: '8px 16px' }}>
            🔄 Reset Counts
          </button>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Powered by <strong>YOLOv11</strong> & <strong>ByteTrack</strong>
        </div>
      </div>
    </div>
  );
}
