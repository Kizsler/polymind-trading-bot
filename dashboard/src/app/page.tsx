"use client";

import React from "react";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Wallet,
  Brain,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import useSWR from "swr";
import { fetcher, Trade } from "@/lib/api";

// Helper to format relative time
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

interface StatusData {
  version: string;
  mode: string;
  daily_pnl: number;
  open_exposure: number;
  wallet_count: number;
}

export default function Home() {
  // Fetch real status from API
  const { data: status, error: statusError, isLoading: statusLoading } = useSWR<StatusData>(
    "/status",
    fetcher,
    { refreshInterval: 5000 }
  );

  // Fetch real trades from API
  const { data: trades } = useSWR<Trade[]>(
    "/trades?limit=50",
    fetcher,
    { refreshInterval: 5000 }
  );

  // Calculate stats from trades
  const totalDecisions = trades?.length || 0;
  const copiedCount = trades?.filter((t) => t.decision === "COPY").length || 0;

  // Build P&L chart data from trades
  const pnlData = React.useMemo(() => {
    if (!trades || trades.length === 0) {
      return [{ time: "Now", pnl: 0 }];
    }

    // Sort trades by timestamp ascending
    const sortedTrades = [...trades].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Calculate cumulative P&L
    let cumPnl = 0;
    const dataPoints = sortedTrades
      .filter((t) => t.pnl !== null && t.pnl !== undefined)
      .map((t) => {
        cumPnl += t.pnl || 0;
        const date = new Date(t.timestamp);
        return {
          time: date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          pnl: cumPnl,
        };
      });

    // Add starting point and current
    if (dataPoints.length === 0) {
      return [{ time: "Now", pnl: 0 }];
    }

    return [{ time: "Start", pnl: 0 }, ...dataPoints];
  }, [trades]);

  const stats = [
    {
      title: "Daily P&L",
      value: status ? `${status.daily_pnl >= 0 ? "+" : ""}$${status.daily_pnl.toFixed(2)}` : "$0.00",
      change: status?.daily_pnl ? `${status.daily_pnl >= 0 ? "+" : ""}${((status.daily_pnl / 1000) * 100).toFixed(1)}%` : "0%",
      trend: status?.daily_pnl && status.daily_pnl >= 0 ? "up" : status?.daily_pnl && status.daily_pnl < 0 ? "down" : "neutral",
      icon: DollarSign,
    },
    {
      title: "Open Exposure",
      value: status ? `$${status.open_exposure.toFixed(2)}` : "$0.00",
      change: "of $2,000 limit",
      trend: "neutral",
      icon: Activity,
    },
    {
      title: "Tracked Wallets",
      value: status?.wallet_count?.toString() || "0",
      change: "Active",
      trend: "up",
      icon: Wallet,
    },
    {
      title: "AI Decisions",
      value: totalDecisions.toString(),
      change: `${copiedCount} copied`,
      trend: "up",
      icon: Brain,
    },
  ];

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Monitor your copy trading performance in real-time
          </p>
        </div>

        {/* Connection Error */}
        {statusError && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">API Connection Error</p>
                  <p className="text-sm text-muted-foreground">
                    Unable to connect to backend at localhost:8000. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {statusLoading && !status && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Connecting to API...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          {stats.map((stat) => (
            <Card key={stat.title} className="bg-card border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  <span
                    className={
                      stat.trend === "up"
                        ? "text-profit"
                        : stat.trend === "down"
                        ? "text-loss"
                        : ""
                    }
                  >
                    {stat.value}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  {stat.trend === "up" && (
                    <TrendingUp className="h-3 w-3 text-profit" />
                  )}
                  {stat.trend === "down" && (
                    <TrendingDown className="h-3 w-3 text-loss" />
                  )}
                  {stat.change}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid gap-4 lg:grid-cols-7 mb-8">
          {/* P&L Chart */}
          <Card className="lg:col-span-4 bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Daily P&L</span>
                <Badge variant="outline" className={status?.daily_pnl && status.daily_pnl >= 0 ? "text-profit border-profit/30" : "text-loss border-loss/30"}>
                  {status ? `${status.daily_pnl >= 0 ? "+" : ""}$${status.daily_pnl.toFixed(2)}` : "$0.00"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={pnlData}>
                    <defs>
                      <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="5%"
                          stopColor="oklch(0.72 0.22 145)"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="oklch(0.72 0.22 145)"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="oklch(0.22 0.01 260)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="time"
                      stroke="oklch(0.6 0.01 260)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="oklch(0.6 0.01 260)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `$${value}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "oklch(0.12 0.01 260)",
                        border: "1px solid oklch(0.22 0.01 260)",
                        borderRadius: "8px",
                        color: "oklch(0.95 0.01 260)",
                      }}
                      formatter={(value) => [`$${(value as number)?.toFixed(2) ?? '0.00'}`, "P&L"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="pnl"
                      stroke="oklch(0.72 0.22 145)"
                      strokeWidth={2}
                      fill="url(#pnlGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Activity Feed */}
          <Card className="lg:col-span-3 bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Live Activity</span>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-profit pulse-live" />
                  <span className="text-xs text-muted-foreground">Live</span>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {(trades || []).slice(0, 4).map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        trade.decision === "COPY"
                          ? "bg-profit/20 text-profit"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {trade.decision === "COPY" ? (
                        <ArrowUpRight className="h-4 w-4" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{trade.wallet_alias || trade.wallet}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-[150px]">
                        {trade.market_id}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-sm font-medium tabular-nums ${
                        (trade.pnl || 0) > 0
                          ? "text-profit"
                          : (trade.pnl || 0) < 0
                          ? "text-loss"
                          : "text-muted-foreground"
                      }`}
                    >
                      {(trade.pnl || 0) > 0 ? "+" : ""}
                      {trade.pnl ? `$${trade.pnl.toFixed(2)}` : "—"}
                    </p>
                    <p className="text-xs text-muted-foreground flex items-center justify-end gap-1">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(trade.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
              {(!trades || trades.length === 0) && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No trades yet
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Trades Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle>Recent Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Wallet
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Market
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Side
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      Size
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      Price
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-muted-foreground">
                      Decision
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      P&L
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(trades || []).map((trade) => (
                    <tr
                      key={trade.id}
                      className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <span className="font-medium">{trade.wallet_alias || trade.wallet}</span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground max-w-[200px] truncate">
                        {trade.market_id}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className={
                            trade.side === "YES"
                              ? "text-profit border-profit/30 bg-profit/10"
                              : "text-loss border-loss/30 bg-loss/10"
                          }
                        >
                          {trade.side}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right tabular-nums">
                        ${trade.size.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-right tabular-nums">
                        {trade.price.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          variant={trade.decision === "COPY" ? "default" : "secondary"}
                          className={
                            trade.decision === "COPY"
                              ? "bg-primary text-primary-foreground"
                              : ""
                          }
                        >
                          {trade.decision}
                        </Badge>
                      </td>
                      <td
                        className={`py-3 px-4 text-right tabular-nums font-medium ${
                          (trade.pnl || 0) > 0
                            ? "text-profit"
                            : (trade.pnl || 0) < 0
                            ? "text-loss"
                            : "text-muted-foreground"
                        }`}
                      >
                        {(trade.pnl || 0) > 0 ? "+" : ""}
                        {trade.pnl ? `$${trade.pnl.toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  ))}
                  {(!trades || trades.length === 0) && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        No trades yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
