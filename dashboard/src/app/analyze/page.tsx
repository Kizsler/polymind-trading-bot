"use client";

import { useMemo, useState, useEffect } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { PnLChart, EquityChart } from "@/components/charts";
import { Card, CardContent } from "@/components/ui/card";
import {
  Home,
  ChevronRight,
  BarChart3,
  TrendingUp,
  Target,
  Percent,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface Trade {
  id: number;
  market_id: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  pnl?: number;
  executed: boolean;
  timestamp: string;
}

export default function AnalyzePage() {
  const { user, profile } = useAuth();
  const supabase = createClient();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch trades from Supabase
  useEffect(() => {
    const fetchTrades = async () => {
      if (!user) {
        setIsLoading(false);
        return;
      }

      const { data } = await supabase
        .from("trades")
        .select("*")
        .eq("user_id", user.id)
        .eq("executed", true)
        .order("timestamp", { ascending: true })
        .limit(500);

      if (data) setTrades(data);
      setIsLoading(false);
    };

    fetchTrades();

    // Subscribe to realtime updates
    const channel = supabase
      .channel("analyze-trades")
      .on("postgres_changes", { event: "*", schema: "public", table: "trades" }, fetchTrades)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, supabase]);

  const startingBalance = profile?.starting_balance || 1000;

  // Compute stats from real trades
  const stats = useMemo(() => {
    if (!trades || trades.length === 0) {
      return {
        totalReturn: 0,
        winRate: 0,
        profitFactor: 0,
        maxDrawdown: 0,
      };
    }

    const closedTrades = trades.filter((t) => t.pnl !== undefined && t.pnl !== null);
    const wins = closedTrades.filter((t) => (t.pnl || 0) > 0);
    const losses = closedTrades.filter((t) => (t.pnl || 0) < 0);

    const totalPnL = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalWins = wins.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalLosses = Math.abs(losses.reduce((sum, t) => sum + (t.pnl || 0), 0));

    // Calculate max drawdown from equity curve
    let peak = startingBalance;
    let maxDD = 0;
    let equity = startingBalance;
    closedTrades.forEach((t) => {
      equity += t.pnl || 0;
      if (equity > peak) peak = equity;
      const dd = ((peak - equity) / peak) * 100;
      if (dd > maxDD) maxDD = dd;
    });

    return {
      totalReturn: (totalPnL / startingBalance) * 100,
      winRate: closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0,
      profitFactor: totalLosses > 0 ? totalWins / totalLosses : totalWins > 0 ? 999 : 0,
      maxDrawdown: maxDD,
    };
  }, [trades, startingBalance]);

  // Compute PnL data from real trades grouped by day
  const pnlData = useMemo(() => {
    const dailyPnL: Record<string, number> = {};

    if (trades && trades.length > 0) {
      trades.forEach((trade) => {
        if (trade.pnl !== undefined && trade.pnl !== null) {
          const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
          dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
        }
      });
    }

    const data = [];
    const now = new Date();
    for (let i = 29; i >= 0; i--) {
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
    const dailyPnL: Record<string, number> = {};

    if (trades && trades.length > 0) {
      trades.forEach((trade) => {
        if (trade.pnl !== undefined && trade.pnl !== null) {
          const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
          dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
        }
      });
    }

    const data = [];
    const now = new Date();
    let equity = startingBalance;
    for (let i = 29; i >= 0; i--) {
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

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8 animate-fade-in">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Analyze</span>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <h1 className="text-2xl font-display font-bold flex items-center gap-3">
          <BarChart3 className="h-6 w-6 text-violet-400" />
          Performance Analysis
        </h1>
        <p className="text-muted-foreground mt-1">
          Detailed metrics and performance tracking
        </p>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <Card className="glass border-border">
          <CardContent className="py-12">
            <div className="flex items-center justify-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              <p className="text-muted-foreground">Loading analytics...</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Stats Grid */}
          <div className="grid gap-4 md:grid-cols-4 mb-8 animate-fade-in stagger-2">
            <Card className="glass border-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Total Return
                  </p>
                </div>
                <p className={`text-2xl font-mono font-bold ${stats.totalReturn >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {stats.totalReturn >= 0 ? "+" : ""}{stats.totalReturn.toFixed(1)}%
                </p>
              </CardContent>
            </Card>

            <Card className="glass border-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="h-4 w-4 text-violet-400" />
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Win Rate
                  </p>
                </div>
                <p className="text-2xl font-mono font-bold">
                  {stats.winRate.toFixed(1)}%
                </p>
              </CardContent>
            </Card>

            <Card className="glass border-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Percent className="h-4 w-4 text-cyan-400" />
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Profit Factor
                  </p>
                </div>
                <p className="text-2xl font-mono font-bold">
                  {stats.profitFactor.toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="glass border-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="h-4 w-4 text-fuchsia-400" />
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Max Drawdown
                  </p>
                </div>
                <p className="text-2xl font-mono font-bold text-red-400">
                  -{stats.maxDrawdown.toFixed(1)}%
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Charts */}
          <div className="space-y-6">
            <div className="animate-fade-in stagger-3">
              <PnLChart data={pnlData} title="Daily P&L ($)" />
            </div>

            <div className="animate-fade-in stagger-4">
              <EquityChart data={equityData} title="Portfolio Value ($)" />
            </div>
          </div>
        </>
      )}
    </ThreeColumnLayout>
  );
}
