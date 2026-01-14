"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  RefreshCw,
  Clock,
  ExternalLink,
  Loader2,
  AlertCircle,
  Bot,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { fetcher, Trade } from "@/lib/api";

function formatTime(timestamp: string) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);

  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

export default function TradesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Fetch trades from API
  const { data: trades, error, isLoading, mutate } = useSWR<Trade[]>(
    "/trades?limit=100",
    fetcher,
    { refreshInterval: 5000 }
  );

  const allTrades = trades || [];

  const filteredTrades = allTrades.filter((trade) => {
    const matchesSearch =
      trade.market_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (trade.wallet_alias || trade.wallet || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (activeTab === "all") return matchesSearch;
    if (activeTab === "copied") return matchesSearch && trade.decision === "COPY";
    if (activeTab === "skipped") return matchesSearch && trade.decision === "SKIP";
    if (activeTab === "ai") return matchesSearch && trade.ai_initiated;
    return matchesSearch;
  });

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const stats = {
    total: allTrades.length,
    copied: allTrades.filter((t) => t.decision === "COPY").length,
    skipped: allTrades.filter((t) => t.decision === "SKIP").length,
    aiTrades: allTrades.filter((t) => t.ai_initiated).length,
    totalPnl: allTrades.reduce((acc, t) => acc + (t.pnl || 0), 0),
  };

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Trades</h1>
          <p className="text-muted-foreground mt-1">
            View all detected trades and AI decisions
          </p>
        </div>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">API Connection Error</p>
                  <p className="text-sm text-muted-foreground">
                    Unable to load trades. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !trades && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading trades...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-5 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums">{stats.total}</div>
              <p className="text-sm text-muted-foreground">Total Signals</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums text-primary">
                {stats.copied}
              </div>
              <p className="text-sm text-muted-foreground">Trades Copied</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums">{stats.skipped}</div>
              <p className="text-sm text-muted-foreground">Trades Skipped</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums text-violet-400 flex items-center gap-2">
                <Bot className="h-5 w-5" />
                {stats.aiTrades}
              </div>
              <p className="text-sm text-muted-foreground">AI Decisions</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div
                className={`text-2xl font-bold tabular-nums ${
                  stats.totalPnl >= 0 ? "text-profit" : "text-loss"
                }`}
              >
                {stats.totalPnl >= 0 ? "+" : ""}${stats.totalPnl.toFixed(2)}
              </div>
              <p className="text-sm text-muted-foreground">Total P&L</p>
            </CardContent>
          </Card>
        </div>

        {/* Trades Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Trade History</CardTitle>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search trades..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64 bg-background"
                  />
                </div>
                <Button variant="outline" size="icon" onClick={() => mutate()}>
                  <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-4">
              <TabsList className="bg-secondary">
                <TabsTrigger value="all">All ({stats.total})</TabsTrigger>
                <TabsTrigger value="copied">Copied ({stats.copied})</TabsTrigger>
                <TabsTrigger value="skipped">Skipped ({stats.skipped})</TabsTrigger>
                <TabsTrigger value="ai" className="gap-1">
                  <Bot className="h-3 w-3" />
                  AI ({stats.aiTrades})
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="relative overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground w-8">
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Time
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Wallet
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                      Market
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-muted-foreground">
                      Action
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-muted-foreground">
                      Side
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      Size
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      Price
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                      P&L
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTrades.map((trade) => (
                    <>
                      <tr
                        key={trade.id}
                        className={`border-b border-border/50 hover:bg-secondary/30 transition-colors ${
                          trade.sell_reasoning ? "cursor-pointer" : ""
                        }`}
                        onClick={() => trade.sell_reasoning && toggleRow(trade.id)}
                      >
                        <td className="py-3 px-4">
                          {trade.sell_reasoning ? (
                            <button className="text-muted-foreground hover:text-foreground">
                              {expandedRows.has(trade.id) ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </button>
                          ) : null}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span className="text-xs">{formatTime(trade.timestamp)}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div>
                            <span className="font-medium">{trade.wallet_alias || "Unknown"}</span>
                            <p className="text-xs text-muted-foreground font-mono">
                              {trade.wallet ? `${trade.wallet.slice(0, 10)}...` : "—"}
                            </p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2 max-w-[250px]">
                            <span className="truncate">{trade.market_title || trade.market_id}</span>
                            <a
                              href={`https://polymarket.com/event/${trade.market_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {trade.ai_initiated && (
                              <Bot className="h-3 w-3 text-violet-400" />
                            )}
                            <Badge
                              variant="outline"
                              className={
                                trade.action === "SELL"
                                  ? "text-amber-400 border-amber-400/30 bg-amber-400/10"
                                  : "text-blue-400 border-blue-400/30 bg-blue-400/10"
                              }
                            >
                              {trade.action === "SELL" ? (
                                <TrendingDown className="h-3 w-3 mr-1" />
                              ) : (
                                <TrendingUp className="h-3 w-3 mr-1" />
                              )}
                              {trade.action || "BUY"}
                            </Badge>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
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
                      {/* Expanded row for AI reasoning */}
                      {expandedRows.has(trade.id) && trade.sell_reasoning && (
                        <tr key={`${trade.id}-expanded`} className="bg-secondary/20">
                          <td colSpan={9} className="py-3 px-4">
                            <div className="flex items-start gap-3 pl-8">
                              <Bot className="h-4 w-4 text-violet-400 mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-sm font-medium text-violet-400 mb-1">AI Reasoning</p>
                                <p className="text-sm text-muted-foreground">{trade.sell_reasoning}</p>
                                {trade.entry_price && trade.exit_price && (
                                  <p className="text-xs text-muted-foreground mt-2">
                                    Entry: ${trade.entry_price.toFixed(4)} → Exit: ${trade.exit_price.toFixed(4)}
                                    {trade.realized_pnl !== undefined && (
                                      <span className={trade.realized_pnl >= 0 ? "text-profit ml-2" : "text-loss ml-2"}>
                                        Realized: {trade.realized_pnl >= 0 ? "+" : ""}${trade.realized_pnl.toFixed(2)}
                                      </span>
                                    )}
                                  </p>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>

              {filteredTrades.length === 0 && !isLoading && (
                <div className="text-center py-12 text-muted-foreground">
                  {searchQuery ? "No trades found matching your search." : "No trades yet."}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
