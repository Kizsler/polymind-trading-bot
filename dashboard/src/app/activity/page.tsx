"use client";

import { useMemo, useState, useEffect } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Home,
  ChevronRight,
  Zap,
  Clock,
  CheckCircle2,
  Circle,
  Activity,
  Search,
  Filter,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

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

export default function ActivityPage() {
  const { user, profile } = useAuth();
  const supabase = createClient();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sideFilter, setSideFilter] = useState<"all" | "YES" | "NO">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "executed" | "pending">("all");

  // Fetch user's trades from Supabase
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
        .order("timestamp", { ascending: false })
        .limit(100);

      if (data) setTrades(data);
      setIsLoading(false);
    };

    fetchTrades();

    // Subscribe to realtime updates
    const channel = supabase
      .channel("activity-trades")
      .on("postgres_changes", { event: "*", schema: "public", table: "trades" }, fetchTrades)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, supabase]);

  const copyPercentage = profile?.copy_percentage || 0.1;

  // Helper function to format relative time
  const getRelativeTime = (timestamp: string) => {
    const now = new Date();
    const tradeTime = new Date(timestamp);
    const diffMs = now.getTime() - tradeTime.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    return `${diffDay}d ago`;
  };

  // Filter trades
  const filteredTrades = useMemo(() => {
    let result = trades;

    // Side filter
    if (sideFilter !== "all") {
      result = result.filter((t) => t.side === sideFilter);
    }

    // Status filter
    if (statusFilter === "executed") {
      result = result.filter((t) => t.executed);
    } else if (statusFilter === "pending") {
      result = result.filter((t) => !t.executed);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.market_title?.toLowerCase().includes(query) ||
          t.market_id.toLowerCase().includes(query) ||
          t.wallet?.toLowerCase().includes(query) ||
          t.wallet_alias?.toLowerCase().includes(query)
      );
    }

    return result;
  }, [trades, sideFilter, statusFilter, searchQuery]);

  // Stats
  const stats = useMemo(() => {
    const executed = trades.filter((t) => t.executed).length;
    const pending = trades.filter((t) => !t.executed).length;
    const totalVolume = trades.reduce((sum, t) => sum + t.size * copyPercentage, 0);
    const totalPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    return { executed, pending, totalVolume, totalPnL };
  }, [trades, copyPercentage]);

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8 animate-fade-in">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Activity</span>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-display font-bold flex items-center gap-3">
              <Zap className="h-6 w-6 text-violet-400" />
              Live Activity
            </h1>
            <p className="text-muted-foreground mt-1">
              Real-time trade activity and execution history
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-sm text-muted-foreground">Real-time</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4 mb-8 animate-fade-in stagger-2">
        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Executed
              </p>
            </div>
            <p className="text-2xl font-mono font-bold">{stats.executed}</p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Circle className="h-4 w-4 text-violet-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Pending
              </p>
            </div>
            <p className="text-2xl font-mono font-bold">{stats.pending}</p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-cyan-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Volume
              </p>
            </div>
            <p className="text-2xl font-mono font-bold">${stats.totalVolume.toFixed(2)}</p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-fuchsia-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Total P&L
              </p>
            </div>
            <p className={`text-2xl font-mono font-bold ${stats.totalPnL >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {stats.totalPnL >= 0 ? "+" : ""}{stats.totalPnL.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="glass border-border mb-6 animate-fade-in stagger-3">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search markets, wallets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-background"
                />
              </div>
            </div>
            <Select value={sideFilter} onValueChange={(v) => setSideFilter(v as typeof sideFilter)}>
              <SelectTrigger className="w-[120px] bg-background">
                <SelectValue placeholder="Side" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sides</SelectItem>
                <SelectItem value="YES">YES</SelectItem>
                <SelectItem value="NO">NO</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
              <SelectTrigger className="w-[140px] bg-background">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="executed">Executed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Activity Feed */}
      <Card className="glass border-border animate-fade-in stagger-4">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-display">
              Trade Activity ({filteredTrades.length})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredTrades.length > 0 ? (
            <div className="space-y-2">
              {filteredTrades.map((trade, i) => (
                <div
                  key={trade.id || i}
                  className={`flex items-center justify-between p-4 rounded-lg border transition-all duration-300 ${
                    trade.executed
                      ? "bg-secondary/30 border-border/50"
                      : "bg-violet-500/5 border-violet-500/20 animate-pulse"
                  }`}
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  <div className="flex items-center gap-4">
                    {/* Status Icon */}
                    <div
                      className={`h-10 w-10 rounded-full flex items-center justify-center ${
                        trade.executed
                          ? trade.side === "YES"
                            ? "bg-emerald-500/10"
                            : "bg-red-500/10"
                          : "bg-violet-500/10"
                      }`}
                    >
                      {trade.executed ? (
                        <CheckCircle2
                          className={`h-5 w-5 ${
                            trade.side === "YES" ? "text-emerald-500" : "text-red-500"
                          }`}
                        />
                      ) : (
                        <Circle className="h-5 w-5 text-violet-400 animate-pulse" />
                      )}
                    </div>

                    {/* Trade Info */}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {trade.market_title || trade.market_id.slice(0, 30) + "..."}
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            trade.side === "YES"
                              ? "border-emerald-500/30 text-emerald-400"
                              : "border-red-500/30 text-red-400"
                          }`}
                        >
                          {trade.side}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-sm text-muted-foreground">
                          {trade.wallet_alias || trade.wallet?.slice(0, 10) + "..."}
                        </span>
                        <span className="text-xs text-muted-foreground">|</span>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {getRelativeTime(trade.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Trade Value & Status */}
                  <div className="text-right">
                    <div className="flex items-center gap-2 justify-end">
                      <span className="text-lg font-mono font-semibold">
                        ${(trade.size * copyPercentage).toFixed(2)}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        @ {(trade.price * 100).toFixed(0)}c
                      </span>
                    </div>
                    <div className="mt-1">
                      {trade.executed ? (
                        trade.pnl !== null && trade.pnl !== undefined ? (
                          <span
                            className={`text-sm font-mono ${
                              trade.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                            }`}
                          >
                            {trade.pnl >= 0 ? "+" : ""}
                            {trade.pnl.toFixed(2)} P&L
                          </span>
                        ) : (
                          <Badge variant="outline" className="text-xs text-muted-foreground">
                            Executed
                          </Badge>
                        )
                      ) : (
                        <Badge variant="outline" className="text-xs text-violet-400 border-violet-500/30">
                          Pending...
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <Activity className="h-16 w-16 mx-auto mb-6 text-muted-foreground/30" />
              <p className="text-xl font-medium text-muted-foreground mb-2">No trading activity</p>
              <p className="text-sm text-muted-foreground/60">
                {searchQuery || sideFilter !== "all" || statusFilter !== "all"
                  ? "No trades match your filters"
                  : "Trades will appear here when the bot executes them"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </ThreeColumnLayout>
  );
}
