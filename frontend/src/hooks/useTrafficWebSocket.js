import { useState, useEffect, useRef, useCallback } from 'react';

export function useTrafficWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(null);
  const [telemetry, setTelemetry] = useState({
    time_sec: 0,
    real_time: '--:--:--',
    inbound_count: 0,
    outbound_count: 0,
    total_count: 0,
    active_vehicles: 0,
    inbound_active: 0,
    outbound_active: 0,
    stall_ratio: 0,
    density_score: 0,
    traffic_level_th: 'คล่องตัว',
    traffic_level_en: 'Smooth',
    traffic_level_emoji: '🟢',
    traffic_level_color: '#10B981',
    class_counts: { Car: 0, Motorcycle: 0, Bus: 0, Truck: 0 },
    new_events: []
  });

  const [eventLogs, setEventLogs] = useState([]);
  const [fps, setFps] = useState(0);
  const wsRef = useRef(null);
  const fpsTimerRef = useRef({ count: 0, lastTime: performance.now() });

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.origin.includes(':5173') ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/stream`;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsPlaying(false);
    };

    ws.onerror = (err) => {
      console.error('WebSocket Error:', err);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'frame') {
          if (msg.image) {
            setCurrentFrame(`data:image/jpeg;base64,${msg.image}`);
          }
          if (msg.telemetry) {
            setTelemetry(msg.telemetry);
            if (msg.telemetry.new_events && msg.telemetry.new_events.length > 0) {
              setEventLogs((prev) => [...msg.telemetry.new_events, ...prev].slice(0, 100));
            }
          }

          // Compute client FPS
          const now = performance.now();
          fpsTimerRef.current.count += 1;
          if (now - fpsTimerRef.current.lastTime >= 1000) {
            setFps(Math.round((fpsTimerRef.current.count * 1000) / (now - fpsTimerRef.current.lastTime)));
            fpsTimerRef.current.count = 0;
            fpsTimerRef.current.lastTime = now;
          }
        } else if (msg.type === 'status') {
          setIsPlaying(msg.playing);
        }
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendCommand = useCallback((command, payload = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...payload }));
    }
  }, []);

  const startStream = useCallback((config) => {
    sendCommand('start', config);
    setIsPlaying(true);
  }, [sendCommand]);

  const pauseStream = useCallback(() => {
    sendCommand('pause');
    setIsPlaying(false);
  }, [sendCommand]);

  const resumeStream = useCallback(() => {
    sendCommand('resume');
    setIsPlaying(true);
  }, [sendCommand]);

  const resetStream = useCallback(() => {
    sendCommand('reset');
    setEventLogs([]);
  }, [sendCommand]);

  const updateConfig = useCallback((config) => {
    sendCommand('update_config', config);
  }, [sendCommand]);

  return {
    isConnected,
    isPlaying,
    currentFrame,
    telemetry,
    eventLogs,
    fps,
    startStream,
    pauseStream,
    resumeStream,
    resetStream,
    updateConfig,
    reconnect: connect
  };
}
