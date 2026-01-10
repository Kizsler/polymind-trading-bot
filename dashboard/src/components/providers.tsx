"use client";

import { WebSocketProvider } from "@/lib/websocket";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

  return <WebSocketProvider url={wsUrl}>{children}</WebSocketProvider>;
}
