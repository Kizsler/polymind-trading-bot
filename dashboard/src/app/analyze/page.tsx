"use client";

import { useMemo } from "react";
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
} from "lucide-react";
import useSWR from "swr";
import { fetcher, Trade } from "@/lib/api";

export default function AnalyzePage() {
  const { data: trades } = useSWR<Trade[]>("/trades?limit=500", fetcher, { refreshInterval: 30000 });

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
    let peak = 1000;
    let maxDD = 0;
    let equity = 1000;
    closedTrades.forEach((t) => {
      equity += t.pnl || 0;
      if (equity > peak) peak = equity;
      const dd = ((peak - equity) / peak) * 100;
      if (dd > maxDD) maxDD = dd;
    });

    return {
      totalReturn: (totalPnL / 1000) * 100,
      winRate: closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0,
      profitFactor: totalLosses > 0 ? totalWins / totalLosses : totalWins > 0 ? 999 : 0,
      maxDrawdown: maxDD,
    };
  }, [trades]);

  // Compute PnL data from real trades grouped by day
  const pnlData = useMemo(() => {
    if (!trades || trades.length === 0) {
      const data = [];
      const now = new Date();
      for (let i = 29; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
          pnl: 0,
        });
      }
      return data;
    }

    const dailyPnL: Record<string, number> = {};
    trades.forEach((trade) => {
      const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
      dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
    });

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
    const startingEquity = 1000;
    if (!trades || trades.length === 0) {
      const data = [];
      const now = new Date();
      for (let i = 29; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
          equity: startingEquity,
        });
      }
      return data;
    }

    const dailyPnL: Record<string, number> = {};
    trades.forEach((trade) => {
      const date = new Date(trade.timestamp).toLocaleDateString("en-US", { day: "numeric", month: "short" });
      dailyPnL[date] = (dailyPnL[date] || 0) + (trade.pnl || 0);
    });

    const data = [];
    const now = new Date();
    let equity = startingEquity;
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
  }, [trades]);

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
          <PnLChart data={pnlData} title="Daily Returns (%)" />
        </div>

        <div className="animate-fade-in stagger-4">
          <EquityChart data={equityData} title="Portfolio Value" />
        </div>
      </div>
    </ThreeColumnLayout>
  );
}
