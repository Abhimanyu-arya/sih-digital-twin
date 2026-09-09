import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * useLiveStream — React hook for WebSocket-based live telemetry streaming.
 *
 * Handles connection lifecycle, automatic reconnection options,
 * server reachability detection, and frame history buffering.
 */
export default function useLiveStream(wsUrl = '/ws/stream') {
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [serverUnreachable, setServerUnreachable] = useState(false);
  const [connectionLost, setConnectionLost] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const [currentFrame, setCurrentFrame] = useState(null);
  const [history, setHistory] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, pct: 0 });
  const [streamMeta, setStreamMeta] = useState(null);

  const wsRef = useRef(null);
  const historyRef = useRef([]);
  const lastConfigRef = useRef({ missionId: 'mission_007', speed: 10 });
  const wasConnectedRef = useRef(false);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const _ensureConnection = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        resolve(wsRef.current);
        return;
      }

      // Close stale socket if any
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (_) {}
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const fullUrl = wsUrl.startsWith('ws') ? wsUrl : `${protocol}//${window.location.host}${wsUrl}`;
      
      let connectionEstablished = false;
      const ws = new WebSocket(fullUrl);

      ws.onopen = () => {
        connectionEstablished = true;
        wasConnectedRef.current = true;
        setIsConnected(true);
        setServerUnreachable(false);
        setConnectionLost(false);
        setErrorMsg(null);
        wsRef.current = ws;
        resolve(ws);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsStreaming(false);
        wsRef.current = null;
        if (wasConnectedRef.current) {
          setConnectionLost(true);
          setErrorMsg('Connection lost to live inference server');
        } else {
          setServerUnreachable(true);
          setErrorMsg('Live server not reachable — start ai_layer/live_server.py');
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setIsConnected(false);
        setIsStreaming(false);
        if (!connectionEstablished) {
          setServerUnreachable(true);
          setErrorMsg('Live server not reachable — start ai_layer/live_server.py');
          reject(new Error('Live server not reachable — start ai_layer/live_server.py'));
        } else {
          setConnectionLost(true);
          setErrorMsg('Connection lost to live inference server');
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'telemetry_frame') {
            setCurrentFrame(msg);
            historyRef.current = [...historyRef.current, msg];
            setHistory(historyRef.current);
            setProgress({
              current: msg.timestamp || 0,
              total: msg.total_rows || 0,
              pct: msg.progress_pct || 0,
            });
          } else if (msg.type === 'stream_started') {
            setIsStreaming(true);
            historyRef.current = [];
            setHistory([]);
            setCurrentFrame(null);
            setStreamMeta({
              mission_id: msg.mission_id,
              fault_label: msg.fault_label,
              callsign: msg.callsign,
              total_rows: msg.total_rows,
            });
          } else if (msg.type === 'stream_ended') {
            setIsStreaming(false);
          } else if (msg.type === 'error') {
            console.error('Server error message:', msg.message);
            setErrorMsg(msg.message);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    });
  }, [wsUrl]);

  const start = useCallback(async (missionId, speed = 10) => {
    lastConfigRef.current = { missionId, speed };
    setServerUnreachable(false);
    setConnectionLost(false);
    setErrorMsg(null);

    try {
      const ws = await _ensureConnection();
      historyRef.current = [];
      setHistory([]);
      setCurrentFrame(null);
      ws.send(JSON.stringify({ action: 'start', mission_id: missionId, speed }));
    } catch (err) {
      console.error('Failed to start live stream:', err.message);
    }
  }, [_ensureConnection]);

  const stop = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'stop' }));
    }
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      historyRef.current = [];
      setHistory([]);
      setCurrentFrame(null);
      wsRef.current.send(JSON.stringify({ action: 'reset' }));
    }
  }, []);

  const setSpeed = useCallback((speed) => {
    lastConfigRef.current.speed = speed;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'set_speed', speed }));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    wasConnectedRef.current = false;
    setIsConnected(false);
    setIsStreaming(false);
    setServerUnreachable(false);
    setConnectionLost(false);
    setErrorMsg(null);
    setCurrentFrame(null);
    historyRef.current = [];
    setHistory([]);
  }, []);

  const reconnect = useCallback(() => {
    wasConnectedRef.current = false;
    const { missionId, speed } = lastConfigRef.current;
    return start(missionId, speed);
  }, [start]);

  return {
    isConnected,
    isStreaming,
    serverUnreachable,
    connectionLost,
    errorMsg,
    currentFrame,
    history,
    progress,
    streamMeta,
    start,
    stop,
    reset,
    setSpeed,
    disconnect,
    reconnect,
  };
}
