"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Copy,
  Loader2,
  AlertCircle,
  Save,
  RotateCcw,
  Filter,
  Search,
  Calendar,
  X,
} from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface Trade {
  id: number;
  market_id: string;
  market_title?: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  pnl?: number;
  executed: boolean;
  timestamp: string;
}

interface WalletData {
  address: string;
  alias: string;
  enabled: boolean;
  scale_factor: number;
  max_trade_size: number | null;
  min_confidence: number;
}

export default function WalletDetailPage() {
  const params = useParams();
  const address = params.address as string;
  const { user } = useAuth();
  const supabase = createClient();

  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Local state for editable controls
  const [scaleFactor, setScaleFactor] = useState<number>(1.0);
  const [maxTradeSize, setMaxTradeSize] = useState<string>("");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Filter states
  const [sideFilter, setSideFilter] = useState<"all" | "YES" | "NO">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFilter, setDateFilter] = useState<"all" | "today" | "week" | "month">("all");
  const [showFilters, setShowFilters] = useState(false);

  // Fetch wallet and trades
  useEffect(() => {
    const fetchData = async () => {
      if (!user) {
        setIsLoading(false);
        setError("Please log in to view wallet details");
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // Fetch wallet details
        const { data: walletData, error: walletError } = await supabase
          .from("wallets")
          .select("*")
          .eq("user_id", user.id)
          .eq("address", address)
          .single();

        let currentWallet: WalletData;

        if (walletError) {
          // If wallet not found, create a placeholder from the address
          if (walletError.code === "PGRST116") {
            currentWallet = {
              address: address,
              alias: address.slice(0, 10) + "...",
              enabled: true,
              scale_factor: 1.0,
              max_trade_size: null,
              min_confidence: 0,
            };
          } else {
            throw walletError;
          }
        } else {
          currentWallet = walletData;
        }

        setWallet(currentWallet);

        // Initialize form state
        setScaleFactor(currentWallet.scale_factor ?? 1.0);
        setMaxTradeSize(currentWallet.max_trade_size?.toString() || "");
        setMinConfidence(currentWallet.min_confidence ?? 0);

        // Fetch trades for this wallet
        const { data: tradesData, error: tradesError } = await supabase
          .from("trades")
          .select("*")
          .eq("user_id", user.id)
          .eq("wallet", address)
          .order("timestamp", { ascending: false })
          .limit(200);

        if (tradesError) {
          console.warn("Trades query error:", tradesError);
          // Don't throw - just show empty trades
          setTrades([]);
        } else {
          setTrades(tradesData || []);
        }
      } catch (err: any) {
        console.error("Failed to fetch wallet data:", JSON.stringify(err, null, 2));
        console.error("Error details:", err?.message, err?.code, err?.details);
        setError(err?.message || err?.code || "Failed to load wallet data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [user, address, supabase]);

  // Debug logging
  useEffect(() => {
    console.log("Auth state:", { user: user?.id, address });
  }, [user, address]);

  // Calculate stats from trades
  const stats = useMemo(() => {
    const executedTrades = trades.filter(t => t.executed);
    const tradesWithPnl = executedTrades.filter(t => t.pnl !== null && t.pnl !== undefined);
    const wins = tradesWithPnl.filter(t => (t.pnl || 0) > 0);
    const totalPnl = tradesWithPnl.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalVolume = executedTrades.reduce((sum, t) => sum + t.size, 0);
    const avgRoi = totalVolume > 0 ? (totalPnl / totalVolume) * 100 : 0;
    const winRate = tradesWithPnl.length > 0 ? (wins.length / tradesWithPnl.length) * 100 : 0;

    return {
      total_pnl: totalPnl,
      win_rate: winRate,
      avg_roi: avgRoi,
      total_trades: executedTrades.length,
    };
  }, [trades]);

  // Filtered trades
  const filteredTrades = useMemo(() => {
    let result = trades.filter(t => t.executed);

    // Side filter
    if (sideFilter !== "all") {
      result = result.filter(t => t.side === sideFilter);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(t =>
        (t.market_title?.toLowerCase().includes(query)) ||
        t.market_id.toLowerCase().includes(query)
      );
    }

    // Date filter
    if (dateFilter !== "all") {
      const now = new Date();
      let cutoff: Date;

      switch (dateFilter) {
        case "today":
          cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          break;
        case "week":
          cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case "month":
          cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
        default:
          cutoff = new Date(0);
      }

      result = result.filter(t => new Date(t.timestamp) >= cutoff);
    }

    return result;
  }, [trades, sideFilter, searchQuery, dateFilter]);

  const handleSave = async () => {
    if (!user || !wallet) return;
    setIsSaving(true);
    try {
      await supabase
        .from("wallets")
        .update({
          scale_factor: scaleFactor,
          max_trade_size: maxTradeSize ? parseFloat(maxTradeSize) : null,
          min_confidence: minConfidence,
        })
        .eq("user_id", user.id)
        .eq("address", address);

      setHasChanges(false);
    } catch (err) {
      console.error("Failed to update wallet controls:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (wallet) {
      setScaleFactor(wallet.scale_factor ?? 1.0);
      setMaxTradeSize(wallet.max_trade_size?.toString() || "");
      setMinConfidence(wallet.min_confidence ?? 0);
      setHasChanges(false);
    }
  };

  const updateField = (setter: (v: any) => void, value: any) => {
    setter(value);
    setHasChanges(true);
  };

  const clearFilters = () => {
    setSideFilter("all");
    setSearchQuery("");
    setDateFilter("all");
  };

  const hasActiveFilters = sideFilter !== "all" || searchQuery || dateFilter !== "all";

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Back Button */}
        <Link
          href="/wallets"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Wallets
        </Link>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30 animate-in fade-in duration-300">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">Error Loading Wallet</p>
                  <p className="text-sm text-muted-foreground">
                    {error}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && (
          <Card className="mb-8 bg-secondary/50 border-border animate-pulse">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading wallet details...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {wallet && !isLoading && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div>
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    {wallet.alias || "Unnamed Wallet"}
                    <Badge
                      variant="outline"
                      className={cn(
                        "transition-colors",
                        wallet.enabled
                          ? "text-profit border-profit/30"
                          : "text-muted-foreground"
                      )}
                    >
                      {wallet.enabled ? "Active" : "Paused"}
                    </Badge>
                  </h1>
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-sm text-muted-foreground font-mono">
                      {address}
                    </code>
                    <button
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => navigator.clipboard.writeText(address)}
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <a
                      href={`https://polymarket.com/profile/${address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-4">
              {[
                {
                  value: `${stats.total_pnl >= 0 ? "+" : ""}$${stats.total_pnl.toFixed(2)}`,
                  label: "Total P&L",
                  color: stats.total_pnl >= 0 ? "text-profit" : "text-loss"
                },
                {
                  value: `${stats.win_rate.toFixed(0)}%`,
                  label: "Win Rate",
                  icon: stats.win_rate > 50 ? TrendingUp : TrendingDown,
                  iconColor: stats.win_rate > 50 ? "text-profit" : "text-loss"
                },
                { value: `${stats.avg_roi.toFixed(1)}%`, label: "Avg ROI" },
                { value: stats.total_trades, label: "Total Trades" },
              ].map((stat, i) => (
                <Card
                  key={i}
                  className="bg-card border-border hover:bg-card/80 transition-colors animate-in fade-in slide-in-from-bottom-2 duration-300"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <CardContent className="pt-6">
                    <div className={cn("text-2xl font-bold flex items-center gap-2", stat.color)}>
                      {stat.value}
                      {stat.icon && <stat.icon className={cn("h-5 w-5", stat.iconColor)} />}
                    </div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Trading Controls */}
            <Card className="bg-card border-border animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ animationDelay: "200ms" }}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Trading Controls</CardTitle>
                  {hasChanges && (
                    <div className="flex items-center gap-2 animate-in fade-in duration-200">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleReset}
                        disabled={isSaving}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset
                      </Button>
                      <Button size="sm" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save Changes
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Scale Factor
                    </label>
                    <p className="text-xs text-muted-foreground/70 mt-0.5 mb-2">
                      Multiply trade sizes by this factor (1.0 = copy exact size)
                    </p>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="10"
                      value={scaleFactor}
                      onChange={(e) => updateField(setScaleFactor, parseFloat(e.target.value) || 1)}
                      className="bg-background"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Max Trade Size ($)
                    </label>
                    <p className="text-xs text-muted-foreground/70 mt-0.5 mb-2">
                      Maximum size per trade (leave empty for no limit)
                    </p>
                    <Input
                      type="number"
                      step="10"
                      min="0"
                      placeholder="No limit"
                      value={maxTradeSize}
                      onChange={(e) => updateField(setMaxTradeSize, e.target.value)}
                      className="bg-background"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Trades Section */}
            <Card className="bg-card border-border animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ animationDelay: "300ms" }}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    Trade History
                    <Badge variant="secondary" className="font-mono">
                      {filteredTrades.length}
                    </Badge>
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowFilters(!showFilters)}
                    className={cn(
                      "gap-2 transition-colors",
                      hasActiveFilters && "border-primary text-primary"
                    )}
                  >
                    <Filter className="h-4 w-4" />
                    Filters
                    {hasActiveFilters && (
                      <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    )}
                  </Button>
                </div>

                {/* Filters */}
                <div
                  className={cn(
                    "grid gap-4 overflow-hidden transition-all duration-300 ease-in-out",
                    showFilters ? "grid-rows-[1fr] opacity-100 mt-4" : "grid-rows-[0fr] opacity-0"
                  )}
                >
                  <div className="min-h-0">
                    <div className="flex flex-wrap gap-3 items-end">
                      {/* Search */}
                      <div className="flex-1 min-w-[200px]">
                        <label className="text-xs text-muted-foreground mb-1 block">Search</label>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            placeholder="Search markets..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 bg-background"
                          />
                        </div>
                      </div>

                      {/* Side Filter */}
                      <div className="w-32">
                        <label className="text-xs text-muted-foreground mb-1 block">Side</label>
                        <Select value={sideFilter} onValueChange={(v) => setSideFilter(v as any)}>
                          <SelectTrigger className="bg-background">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All</SelectItem>
                            <SelectItem value="YES">
                              <span className="flex items-center gap-2">
                                <span className="h-2 w-2 rounded-full bg-profit" />
                                YES
                              </span>
                            </SelectItem>
                            <SelectItem value="NO">
                              <span className="flex items-center gap-2">
                                <span className="h-2 w-2 rounded-full bg-loss" />
                                NO
                              </span>
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Date Filter */}
                      <div className="w-36">
                        <label className="text-xs text-muted-foreground mb-1 block">Time Period</label>
                        <Select value={dateFilter} onValueChange={(v) => setDateFilter(v as any)}>
                          <SelectTrigger className="bg-background">
                            <Calendar className="h-4 w-4 mr-2" />
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Time</SelectItem>
                            <SelectItem value="today">Today</SelectItem>
                            <SelectItem value="week">Last 7 Days</SelectItem>
                            <SelectItem value="month">Last 30 Days</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Clear Filters */}
                      {hasActiveFilters && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={clearFilters}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <X className="h-4 w-4 mr-1" />
                          Clear
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>

              <CardContent>
                {filteredTrades.length > 0 ? (
                  <div className="space-y-2">
                    {filteredTrades.map((trade, i) => (
                      <div
                        key={trade.id}
                        className={cn(
                          "flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-all duration-200",
                          "animate-in fade-in slide-in-from-left-2"
                        )}
                        style={{ animationDelay: `${Math.min(i * 30, 300)}ms` }}
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          {/* Side indicator */}
                          <div
                            className={cn(
                              "h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0",
                              trade.side === "YES" ? "bg-profit/10" : "bg-loss/10"
                            )}
                          >
                            {trade.side === "YES" ? (
                              <TrendingUp className="h-4 w-4 text-profit" />
                            ) : (
                              <TrendingDown className="h-4 w-4 text-loss" />
                            )}
                          </div>

                          {/* Market info */}
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">
                              {trade.market_title || trade.market_id.slice(0, 30) + "..."}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatDate(trade.timestamp)}
                            </p>
                          </div>
                        </div>

                        {/* Trade details */}
                        <div className="flex items-center gap-4 flex-shrink-0">
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              trade.side === "YES"
                                ? "border-profit/30 text-profit"
                                : "border-loss/30 text-loss"
                            )}
                          >
                            {trade.side}
                          </Badge>
                          <div className="text-right">
                            <p className="text-sm font-mono font-medium">
                              ${trade.size.toFixed(2)}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono">
                              @ {trade.price.toFixed(2)}
                            </p>
                          </div>
                          {trade.pnl !== null && trade.pnl !== undefined && (
                            <div className={cn(
                              "text-sm font-mono font-semibold w-20 text-right",
                              trade.pnl >= 0 ? "text-profit" : "text-loss"
                            )}>
                              {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground animate-in fade-in duration-300">
                    {hasActiveFilters ? (
                      <>
                        <Filter className="h-8 w-8 mx-auto mb-3 opacity-50" />
                        <p>No trades match your filters</p>
                        <Button
                          variant="link"
                          size="sm"
                          onClick={clearFilters}
                          className="mt-2"
                        >
                          Clear filters
                        </Button>
                      </>
                    ) : (
                      <>
                        <TrendingUp className="h-8 w-8 mx-auto mb-3 opacity-50" />
                        <p>No trades yet for this wallet</p>
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
