"use client";

import { useEffect, useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Square,
  Activity,
  Wallet,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface CryptoPrice {
  symbol: string;
  price: number;
  change24h: number;
}

interface Trade {
  pnl?: number;
  executed: boolean;
}

export function StatusPanel() {
  const { user, profile } = useAuth();
  const supabase = createClient();

  const [trades, setTrades] = useState<Trade[]>([]);
  const [isToggling, setIsToggling] = useState(false);
  const [cryptoPrices, setCryptoPrices] = useState<CryptoPrice[]>([
    { symbol: "BTC", price: 0, change24h: 0 },
    { symbol: "ETH", price: 0, change24h: 0 },
    { symbol: "SOL", price: 0, change24h: 0 },
  ]);
  const [pricesLoading, setPricesLoading] = useState(true);

  // Fetch user's trades from Supabase
  useEffect(() => {
    const fetchTrades = async () => {
      if (!user) return;

      const { data } = await supabase
        .from("trades")
        .select("pnl, executed")
        .eq("user_id", user.id);

      if (data) setTrades(data);
    };

    fetchTrades();

    // Subscribe to realtime updates
    const channel = supabase
      .channel("status-trades")
      .on("postgres_changes", { event: "*", schema: "public", table: "trades" }, fetchTrades)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, supabase]);

  // Calculate PnL from trades
  const pnlData = useMemo(() => {
    const executedTrades = trades.filter(t => t.executed && t.pnl !== null && t.pnl !== undefined);
    const wins = executedTrades.filter(t => (t.pnl || 0) > 0);
    const losses = executedTrades.filter(t => (t.pnl || 0) < 0);
    const totalPnl = executedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);

    const winRate = executedTrades.length > 0
      ? ((wins.length / executedTrades.length) * 100).toFixed(1)
      : "0.0";

    return {
      total_pnl: totalPnl.toFixed(2),
      win_count: wins.length,
      loss_count: losses.length,
      win_rate: winRate,
    };
  }, [trades]);

  // Fetch crypto prices from CoinGecko with graceful fallback
  useEffect(() => {
    const controller = new AbortController();

    const fetchPrices = async () => {
      try {
        const res = await fetch(
          "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true",
          {
            signal: controller.signal,
            headers: { "Accept": "application/json" }
          }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setCryptoPrices([
          { symbol: "BTC", price: data.bitcoin?.usd || 0, change24h: data.bitcoin?.usd_24h_change || 0 },
          { symbol: "ETH", price: data.ethereum?.usd || 0, change24h: data.ethereum?.usd_24h_change || 0 },
          { symbol: "SOL", price: data.solana?.usd || 0, change24h: data.solana?.usd_24h_change || 0 },
        ]);
        setPricesLoading(false);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setPricesLoading(false);
      }
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 60000);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  // Get values from profile
  const startingBalance = profile?.starting_balance || 1000;
  const copyPercentage = profile?.copy_percentage || 0.1;
  const isRunning = profile?.bot_status === "running";
  const totalTrades = trades.length;

  const handleToggleBot = async () => {
    if (!user) return;
    setIsToggling(true);
    try {
      await supabase
        .from("profiles")
        .update({ bot_status: isRunning ? "stopped" : "running" })
        .eq("id", user.id);

      // Refresh profile would be needed here - for now just toggle local state
      window.location.reload();
    } catch (err) {
      console.error("Failed to toggle bot:", err);
    } finally {
      setIsToggling(false);
    }
  };

  const totalPnl = parseFloat(pnlData.total_pnl);
  const accountValue = startingBalance + totalPnl;

  return (
    <aside className="w-80 h-screen bg-card/30 border-l border-border p-6 flex flex-col gap-6 overflow-auto">
      {/* Wallet Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Your Wallet</span>
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          Paper Mode
        </span>
      </div>

      {/* Status */}
      <div className="glass rounded-xl p-4 space-y-4">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Status</p>
          <div className="flex items-center gap-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              isRunning ? "bg-emerald-500 animate-pulse-live" : "bg-red-500"
            )} />
            <span className="text-lg font-display font-semibold">
              {isRunning ? "Running" : "Stopped"}
            </span>
          </div>
        </div>

        <div className="flex gap-2">
          <Badge variant="outline" className={cn(
            "text-xs",
            isRunning ? "border-emerald-500/30 text-emerald-400" : "border-muted"
          )}>
            {isRunning ? "Active" : "Inactive"}
          </Badge>
          <Badge variant="outline" className="text-xs border-violet-500/30 text-violet-400">
            Paper
          </Badge>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="glass rounded-xl p-4 space-y-3">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          Quick Stats
        </p>

        {/* Main Balance Display */}
        <div className="bg-gradient-to-r from-violet-500/10 to-emerald-500/10 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Starting Balance</span>
            <span className="text-sm font-mono">${startingBalance.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Realized P&L</span>
            <span className={cn(
              "text-sm font-mono font-semibold",
              totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
              {totalPnl >= 0 ? "+" : ""}${pnlData.total_pnl}
            </span>
          </div>
          {pnlData.win_count + pnlData.loss_count > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-xs text-muted-foreground">Win Rate</span>
              <span className="text-sm font-mono font-semibold text-amber-400">
                {pnlData.win_rate}% ({pnlData.win_count}W / {pnlData.loss_count}L)
              </span>
            </div>
          )}
          <Separator className="bg-border/50" />
          <div className="flex justify-between items-center">
            <span className="text-xs font-medium">Account Value</span>
            <span className={cn(
              "text-lg font-mono font-bold",
              accountValue >= startingBalance ? "text-emerald-400" : "text-red-400"
            )}>
              ${accountValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-muted-foreground">Total Trades</p>
            <p className="text-lg font-mono font-semibold">
              {totalTrades}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Copy %</p>
            <p className="text-lg font-mono font-semibold">
              {(copyPercentage * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>

      {/* Live Crypto Prices */}
      <div className="glass rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
            Crypto Prices
          </p>
          <Activity className="h-3 w-3 text-emerald-500 animate-pulse-live" />
        </div>

        <div className="space-y-2">
          {cryptoPrices.map((crypto) => (
            <div key={crypto.symbol} className="flex items-center justify-between py-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{crypto.symbol}</span>
              </div>
              <div className="text-right">
                {pricesLoading ? (
                  <p className="text-sm font-mono text-muted-foreground">Loading...</p>
                ) : crypto.price > 0 ? (
                  <>
                    <p className="text-sm font-mono">
                      ${crypto.price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                    <p className={cn(
                      "text-xs font-mono",
                      crypto.change24h >= 0 ? "text-profit" : "text-loss"
                    )}>
                      {crypto.change24h >= 0 ? "+" : ""}{crypto.change24h.toFixed(2)}%
                    </p>
                  </>
                ) : (
                  <p className="text-sm font-mono text-muted-foreground">N/A</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Start/Stop Button */}
      <div className="mt-auto">
        <Button
          className={cn(
            "w-full gap-2 font-display font-medium",
            isRunning
              ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30"
              : "gradient-violet text-white hover:opacity-90"
          )}
          size="lg"
          onClick={handleToggleBot}
          disabled={isToggling}
        >
          {isToggling ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {isRunning ? "Stopping..." : "Starting..."}
            </>
          ) : isRunning ? (
            <>
              <Square className="h-4 w-4" />
              Stop Bot
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Start Bot
            </>
          )}
        </Button>
      </div>

      {/* Paper Trading Summary */}
      <div className="glass rounded-xl p-4 space-y-2">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-3">
          Paper Account
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Starting Balance</span>
            <span className="font-mono">${startingBalance.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Realized P&L</span>
            <span className={cn(
              "font-mono",
              totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
              {totalPnl >= 0 ? "+" : ""}${pnlData.total_pnl}
            </span>
          </div>
          {pnlData.win_count + pnlData.loss_count > 0 && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Win Rate</span>
              <span className="font-mono text-amber-400">
                {pnlData.win_rate}%
              </span>
            </div>
          )}
        </div>
        <Separator className="my-3" />
        <div className="flex justify-between items-center">
          <div>
            <p className="text-xs text-muted-foreground">Current Value</p>
            <span className={cn(
              "text-lg font-display font-bold",
              totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
              ${accountValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {new Date().toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}
          </span>
        </div>
      </div>
    </aside>
  );
}
