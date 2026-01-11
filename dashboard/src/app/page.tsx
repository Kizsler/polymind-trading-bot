"use client";

import { useMemo, useEffect, useState } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { PnLChart, EquityChart, TradeTimeline } from "@/components/charts";
import { PositionsBreakdown } from "@/components/positions-breakdown";
import { WalletPerformance } from "@/components/wallet-performance";
import { PnLSummary } from "@/components/pnl-summary";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Home,
  ChevronRight,
  Search,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

// Get singleton client outside component
const supabase = createClient();

interface Trade {
  id: number;
  market_id: string;
  market_title?: string;
  wallet: string;
  wallet_alias?: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  pnl?: number;
  executed: boolean;
  timestamp: string;
}

export default function DashboardPage() {
  const { user, profile, loading: authLoading } = useAuth();
  const [trades, setTrades] = useState<Trade[]>([]);

  // Fetch user's trades from Supabase
  useEffect(() => {
    if (!user) return;

    const fetchTrades = async () => {
      const { data } = await supabase
        .from("trades")
        .select("*")
        .eq("user_id", user.id)
        .order("timestamp", { ascending: false })
        .limit(100);

      if (data) setTrades(data);
    };

    fetchTrades();

    // Subscribe to realtime updates (unique channel per user)
    const channel = supabase
      .channel(`trades-${user.id}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "trades" }, fetchTrades)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user]);

  const startingBalance = profile?.starting_balance ?? 0;

  // Compute PnL data from real trades grouped by day
  // NOTE: Hooks must be called before any conditional returns
  const pnlData = useMemo(() => {
    if (!trades || trades.length === 0) {
      // Return empty placeholder for last 14 days
      const data = [];
      const now = new Date();
      for (let i = 13; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
          pnl: 0,
        });
      }
      return data;
    }

    // Group trades by day and sum PnL
    const dailyPnL: Record<string, number> = {};
    trades.forEach((trade) => {
      const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
      dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
    });

    // Get last 14 days
    const data = [];
    const now = new Date();
    for (let i = 13; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString("en-US", { day: "numeric", month: "short" });
      data.push({
        date: dateStr,
        pnl: dailyPnL[dateStr] || 0,
      });
    }
    return data;
  }, [trades]);

  // Compute equity curve from trades
  const equityData = useMemo(() => {
    if (!trades || trades.length === 0) {
      const data = [];
      const now = new Date();
      for (let i = 13; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
          equity: startingBalance,
        });
      }
      return data;
    }

    // Group trades by day and compute cumulative equity
    const dailyPnL: Record<string, number> = {};
    trades.forEach((trade) => {
      const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
      dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
    });

    const data = [];
    const now = new Date();
    let equity = startingBalance;
    for (let i = 13; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString("en-US", { day: "numeric", month: "short" });
      equity += dailyPnL[dateStr] || 0;
      data.push({
        date: dateStr,
        equity: Math.max(equity, 0),
      });
    }
    return data;
  }, [trades, startingBalance]);

  // Show loading until auth is ready
  if (authLoading) {
    return (
      <ThreeColumnLayout>
        <div className="flex items-center justify-center h-64">
          <Search className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </ThreeColumnLayout>
    );
  }

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb & Search */}
      <div className="flex items-center justify-between mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Home className="h-4 w-4" />
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Overview</span>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 w-64"
          />
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="account" className="mb-8 animate-fade-in stagger-1">
        <TabsList className="bg-secondary/50 border border-border">
          <TabsTrigger value="account">Account Information</TabsTrigger>
          <TabsTrigger value="instance">Bot Performance</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Charts Grid */}
      <div className="space-y-6">
        {/* PnL Summary - Most important, at the top */}
        <div className="animate-fade-in stagger-2">
          <PnLSummary />
        </div>

        {/* Trade Timeline */}
        <div className="animate-fade-in stagger-3">
          <TradeTimeline />
        </div>

        {/* Two-column grid for Positions and Wallet Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in stagger-4">
          <PositionsBreakdown />
          <WalletPerformance />
        </div>

        <div className="animate-fade-in stagger-5">
          <PnLChart data={pnlData} />
        </div>

        <div className="animate-fade-in stagger-6">
          <EquityChart data={equityData} />
        </div>

      </div>
    </ThreeColumnLayout>
  );
}
