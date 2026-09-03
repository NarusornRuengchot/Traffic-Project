import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { MetricCards } from './components/MetricCards';
import { VideoPlayer } from './components/VideoPlayer';
import { ControlPanel } from './components/ControlPanel';
import { VehicleBreakdown } from './components/VehicleBreakdown';
import { AnalyticsCharts } from './components/AnalyticsCharts';
import { EventLogTable } from './components/EventLogTable';
import { useTrafficWebSocket } from './hooks/useTrafficWebSocket';
import { api } from './services/api';

export default function App() {
  const [theme, setTheme] = useState('dark');
  const [showCalibration, setShowCalibration] = useState(false);
  const [restCalibrationPreview, setRestCalibrationPreview] = useState(null);
  const abortControllerRef = React.useRef(null);

  // Calibration and Stream Settings
  const [config, setConfig] = useState({
    video_path: 'IMG_1357.MOV',
    model_name: 'yolo11n.pt',
    conf_threshold: 0.25,

    line_y_ratio: 0.50,
    mid_x_ratio: 0.45,
    swap_directions: false,
    target_classes: ['Car', 'Motorcycle', 'Bus', 'Truck']
  });

  const {
    isConnected,
    isPlaying,
    currentFrame,
    calibrationPreview: wsCalibrationPreview,
    modelStatus,
    telemetry,
    eventLogs,
    fps,
    startStream,
    pauseStream,
    resumeStream,
    resetStream,
    updateConfig,
    updateConfigDebounced,
    requestPreview,
    requestPreviewDebounced
  } = useTrafficWebSocket();

  // Active calibration preview prioritizes real-time WebSocket preview
  const activeCalibrationPreview = wsCalibrationPreview || restCalibrationPreview;

  // Apply Theme to DOM
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleConfigChange = (key, value) => {
    const updated = { ...config, [key]: value };
    setConfig(updated);

    if (isPlaying) {
      // Debounce parameter updates over WebSocket during playback (prevents slider event flooding)
      updateConfigDebounced(updated, 100);
    } else if (showCalibration) {
      if (isConnected) {
        // Fast, zero-lag calibration preview directly over WebSocket (prevents HTTP API spam)
        requestPreviewDebounced(updated, 80);
      } else {
        // Fallback to REST with AbortController to cancel previous in-flight requests
        fetchCalibrationPreviewREST(updated);
      }
    }
  };

  const fetchCalibrationPreviewREST = async (currentCfg = config) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const res = await api.getCalibrationPreview(
        currentCfg.video_path,
        currentCfg.line_y_ratio,
        currentCfg.mid_x_ratio,
        currentCfg.swap_directions,
        abortControllerRef.current.signal
      );
      if (res && res.preview) {
        setRestCalibrationPreview(`data:image/jpeg;base64,${res.preview}`);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Failed to get calibration preview', err);
      }
    }
  };

  const handleToggleCalibration = () => {
    const nextState = !showCalibration;
    setShowCalibration(nextState);
    if (nextState) {
      if (isConnected) {
        requestPreview(config);
      } else {
        fetchCalibrationPreviewREST(config);
      }
    }
  };

  const handleStartStream = () => {
    setShowCalibration(false);
    startStream(config);
  };

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '20px 24px' }}>
      {/* Top Header */}
      <Header
        isConnected={isConnected}
        isPlaying={isPlaying}
        fps={fps}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* KPI Metric Summary Cards */}
      <MetricCards telemetry={telemetry} />

      {/* Main Grid: Left Control Panel, Center Video, Right Analytics */}
      <div className="dashboard-grid">
        {/* Left Column: Control Panel & Settings */}
        <div>
          <ControlPanel
            config={config}
            onChangeConfig={handleConfigChange}
            onToggleCalibrationPreview={handleToggleCalibration}
            showCalibration={showCalibration}
            modelStatus={modelStatus}
          />
        </div>

        {/* Center Column: Video Stream & Event Logs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <VideoPlayer
            currentFrame={currentFrame}
            isPlaying={isPlaying}
            onStart={handleStartStream}
            onPause={pauseStream}
            onResume={resumeStream}
            onReset={resetStream}
            calibrationPreview={activeCalibrationPreview}
            showCalibration={showCalibration}
          />

          <EventLogTable eventLogs={eventLogs} />
        </div>

        {/* Right Column: Breakdown & Real-time Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <VehicleBreakdown
            classCounts={telemetry.class_counts || {}}
            totalCount={telemetry.total_count || 0}
          />

          <AnalyticsCharts telemetry={telemetry} isPlaying={isPlaying} />
        </div>
      </div>
    </div>
  );
}
