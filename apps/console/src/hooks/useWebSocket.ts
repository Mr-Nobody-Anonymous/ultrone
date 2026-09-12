import { useEffect, useRef, useCallback } from 'react';
import { useConnectionStore } from '../store/connectionStore';

interface WebSocketOptions {
  url?: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (err: Event) => void;
}

export function useWebSocket(options: WebSocketOptions = {}) {
  const {
    url = (typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
          (typeof window !== 'undefined' ? window.location.host : 'localhost:8000') + '/ws/stream',
    autoReconnect = true,
    reconnectInterval = 3000,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  const { setWsStatus, setLastPing, incrementMessages } = useConnectionStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setWsStatus('connecting');
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        onOpen?.();

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const start = performance.now();
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
            setLastPing(Math.round(performance.now() - start));
          }
        }, 10000);
      };

      ws.onmessage = (event) => {
        incrementMessages();
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch {
          onMessage?.(event.data);
        }
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        onClose?.();

        if (autoReconnect) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (err) => {
        setWsStatus('error');
        onError?.(err);
      };
    } catch {
      setWsStatus('error');
    }
  }, [url, autoReconnect, reconnectInterval, onMessage, onOpen, onClose, onError, setWsStatus, setLastPing, incrementMessages]);

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setWsStatus('disconnected');
  }, [setWsStatus]);

  useEffect(() => {
    // Only connect if running in a client environment
    if (typeof window !== 'undefined') {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { sendMessage, disconnect, reconnect: connect };
}

export default useWebSocket;
