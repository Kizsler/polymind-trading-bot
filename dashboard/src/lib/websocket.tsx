"use client";

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { mutate } from "swr";

type ConnectionStatus = "connecting" | "connected" | "disconnected";

interface WebSocketContextType {
  status: ConnectionStatus;
  lastMessage: WebSocketMessage | null;
}

interface WebSocketMessage {
  type: "trade" | "status" | "settings" | "wallet";
  data: unknown;
}

const WebSocketContext = createContext<WebSocketContextType>({
  status: "disconnected",
  lastMessage: null,
});

export function useWebSocket() {
  return useContext(WebSocketContext);
}

interface WebSocketProviderProps {
  children: React.ReactNode;
  url?: string;
}

export function WebSocketProvider({
  children,
  url = "ws://localhost:8000/ws",
}: WebSocketProviderProps) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        reconnectAttemptsRef.current = 0;
        console.log("[WebSocket] Connected");
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          // Invalidate SWR cache based on message type
          switch (message.type) {
            case "trade":
              mutate("/trades");
              mutate("/status"); // Trades affect status
              break;
            case "status":
              mutate("/status");
              break;
            case "settings":
              mutate("/settings");
              break;
            case "wallet":
              mutate("/wallets");
              break;
          }
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        console.log("[WebSocket] Disconnected");

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current += 1;
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          console.log("[WebSocket] Max reconnection attempts reached");
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
      };
    } catch (err) {
      console.error("[WebSocket] Failed to connect:", err);
      setStatus("disconnected");
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return (
    <WebSocketContext.Provider value={{ status, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
}
