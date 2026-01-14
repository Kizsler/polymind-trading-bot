"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Wallet,
  Activity,
  Settings,
  Brain,
  TrendingUp,
  Radio,
  Wifi,
  WifiOff,
  Filter,
  GitCompare,
  ClipboardList,
  User,
  Zap,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/lib/websocket";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

interface StatusData {
  mode: string;
  wallets_count: number;
}

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Activity", href: "/activity", icon: Zap },
  { name: "Wallets", href: "/wallets", icon: Wallet },
  { name: "Trades", href: "/trades", icon: Activity },
  { name: "AI Log", href: "/ai-log", icon: Bot },
  { name: "Orders", href: "/orders", icon: ClipboardList },
  { name: "Filters", href: "/filters", icon: Filter },
  { name: "Arbitrage", href: "/arbitrage", icon: GitCompare },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Account", href: "/account", icon: User },
];

export function Sidebar() {
  const pathname = usePathname();
  const { status: wsStatus } = useWebSocket();
  const { data: statusData } = useSWR<StatusData>("/status", fetcher, {
    refreshInterval: wsStatus === "connected" ? 0 : 10000, // Only poll if WS disconnected
  });

  const isConnected = wsStatus === "connected";
  const mode = statusData?.mode || "paper";
  const walletsCount = statusData?.wallets_count ?? 0;

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-border px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary glow-primary">
            <Brain className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">PolyMind</h1>
            <p className="text-xs text-muted-foreground">Trading Bot</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
                {item.name}
                {isActive && (
                  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary pulse-live" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Status Footer */}
        <div className="border-t border-border p-4">
          <div className="rounded-lg bg-card p-3">
            <div className="flex items-center gap-2">
              <Radio className={cn("h-4 w-4", mode === "live" ? "text-loss" : "text-profit", "pulse-live")} />
              <span className={cn("text-xs font-medium", mode === "live" ? "text-loss" : "text-profit")}>
                {mode === "live" ? "Live Trading" : "Paper Trading"}
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>{walletsCount} wallet{walletsCount !== 1 ? "s" : ""} tracked</span>
              <span
                className={cn(
                  "flex items-center gap-1",
                  isConnected ? "text-profit" : "text-muted-foreground"
                )}
                title={isConnected ? "WebSocket connected" : "WebSocket disconnected"}
              >
                {isConnected ? (
                  <>
                    <Wifi className="h-3 w-3" />
                    Live
                  </>
                ) : (
                  <>
                    <WifiOff className="h-3 w-3" />
                    Offline
                  </>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
