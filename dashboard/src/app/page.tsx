"use client";

import { useMemo } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { PnLChart, EquityChart } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Home,
  ChevronRight,
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
} from "lucide-react";
import useSWR from "swr";
import { fetcher, Trade, Status } from "@/lib/api";

export default function DashboardPage() {
  const { data: status } = useSWR<Status>("/status", fetcher, { refreshInterval: 5000 });
  const { data: trades } = useSWR<Trade[]>("/trades?limit=100", fetcher, { refreshInterval: 10000 });

  // Compute PnL data from real trades grouped by day
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
    const startingEquity = 1000; // Starting balance
    if (!trades || trades.length === 0) {
      const data = [];
      const now = new Date();
      for (let i = 13; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        data.push({
          date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
          equity: startingEquity,
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
    let equity = startingEquity;
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
  }, [trades]);

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
        <div className="animate-fade-in stagger-2">
          <PnLChart data={pnlData} />
        </div>

        <div className="animate-fade-in stagger-3">
          <EquityChart data={equityData} />
        </div>

        {/* Recent Trades */}
        <Card className="glass border-border animate-fade-in stagger-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-display">Recent Trades</CardTitle>
              <Activity className="h-4 w-4 text-emerald-500 animate-pulse-live" />
            </div>
          </CardHeader>
          <CardContent>
            {trades && trades.length > 0 ? (
              <div className="space-y-3">
                {trades.slice(0, 5).map((trade, i) => (
                  <div
                    key={trade.id || i}
                    className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                        trade.side === "YES" ? "bg-emerald-500/10" : "bg-red-500/10"
                      }`}>
                        {trade.side === "YES" ? (
                          <TrendingUp className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {trade.market_title || trade.market_id.slice(0, 20) + "..."}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {trade.wallet_alias || trade.wallet.slice(0, 10) + "..."}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-mono">${trade.size.toFixed(2)}</p>
                      <Badge variant="outline" className={`text-xs ${
                        trade.side === "YES"
                          ? "border-emerald-500/30 text-emerald-400"
                          : "border-red-500/30 text-red-400"
                      }`}>
                        {trade.side}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">
                No recent trades
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </ThreeColumnLayout>
  );
}
