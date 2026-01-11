"use client";

import { WebSocketProvider } from "@/lib/websocket";
import { AuthProvider } from "@/lib/supabase/auth-context";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Only enable WebSocket if explicitly configured (not in production without backend)
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;

  return (
    <AuthProvider>
      {wsUrl ? (
        <WebSocketProvider url={wsUrl}>{children}</WebSocketProvider>
      ) : (
        children
      )}
    </AuthProvider>
  );
}
