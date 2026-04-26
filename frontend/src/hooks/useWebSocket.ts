"use client";
import { useEffect, useRef, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(onMessage: (event: string, data: unknown) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryDelay = useRef(3000);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    let ws: WebSocket;
    try {
      ws = new WebSocket(`${WS_URL}/ws`);
    } catch {
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      retryDelay.current = 3000;
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 30000);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        onMessageRef.current(msg.event, msg.data);
      } catch {}
    };

    ws.onclose = () => {
      if (pingRef.current) clearInterval(pingRef.current);
      // Exponential backoff: 3s → 6s → 12s → max 30s
      retryDelay.current = Math.min(retryDelay.current * 2, 30000);
      reconnectRef.current = setTimeout(connect, retryDelay.current);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (pingRef.current) clearInterval(pingRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
