"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Square,
  Activity,
  Wallet,
} from "lucide-react";
import useSWR from "swr";
import { fetcher, Status } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CryptoPrice {
  symbol: string;
  price: number;
  change24h: number;
}

export function StatusPanel() {
  const { data: status } = useSWR<Status>("/status", fetcher, {
    refreshInterval: 5000
  });
  const [cryptoPrices, setCryptoPrices] = useState<CryptoPrice[]>([]);

  // Fetch crypto prices from CoinGecko
  useEffect(() => {
    const fetchPrices = async () => {
      try {
        const res = await fetch(
          "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
        );
        const data = await res.json();
        setCryptoPrices([
          { symbol: "BTC", price: data.bitcoin?.usd || 0, change24h: data.bitcoin?.usd_24h_change || 0 },
          { symbol: "ETH", price: data.ethereum?.usd || 0, change24h: data.ethereum?.usd_24h_change || 0 },
          { symbol: "SOL", price: data.solana?.usd || 0, change24h: data.solana?.usd_24h_change || 0 },
        ]);
      } catch (err) {
        console.error("Failed to fetch crypto prices:", err);
      }
    };

    fetchPrices();
    const interval = setInterval(fetchPrices, 30000);
    return () => clearInterval(interval);
  }, []);

  const isRunning = status?.is_running && !status?.emergency_stop;
  const isPaper = status?.mode === "paper";

  return (
    <aside className="w-80 h-screen bg-card/30 border-l border-border p-6 flex flex-col gap-6 overflow-auto">
      {/* Wallet Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Your Wallet</span>
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          {isPaper ? "Paper Mode" : "Live Mode"}
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
              {status?.emergency_stop ? "Emergency Stop" : isRunning ? "Running" : "Stopped"}
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
            {isPaper ? "Paper" : "Live"}
          </Badge>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="glass rounded-xl p-4 space-y-3">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          Quick Stats
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-muted-foreground">Daily PnL</p>
            <p className={cn(
              "text-lg font-mono font-semibold",
              (status?.daily_pnl || 0) >= 0 ? "text-profit" : "text-loss"
            )}>
              {(status?.daily_pnl || 0) >= 0 ? "+" : ""}${(status?.daily_pnl || 0).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Exposure</p>
            <p className="text-lg font-mono font-semibold">
              ${(status?.open_exposure || 0).toFixed(0)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Trades</p>
            <p className="text-lg font-mono font-semibold">
              {status?.total_trades || 0}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Wallets</p>
            <p className="text-lg font-mono font-semibold">
              {status?.wallets_count || 0}
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
                <p className="text-sm font-mono">
                  ${crypto.price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
                <p className={cn(
                  "text-xs font-mono",
                  crypto.change24h >= 0 ? "text-profit" : "text-loss"
                )}>
                  {crypto.change24h >= 0 ? "+" : ""}{crypto.change24h.toFixed(2)}%
                </p>
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
        >
          {isRunning ? (
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

      {/* Summary */}
      <div className="glass rounded-xl p-4 space-y-2">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-3">
          Summary
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Net profit</span>
            <span className="font-mono">-</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Profit factor</span>
            <span className="font-mono">0.00</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Win rate</span>
            <span className="font-mono">0.00%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Max drawdown</span>
            <span className="font-mono">0.00%</span>
          </div>
        </div>
        <Separator className="my-3" />
        <div className="flex justify-between items-center">
          <span className="text-lg font-display font-bold">$0.00</span>
          <span className="text-xs text-muted-foreground">
            {new Date().toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}
          </span>
        </div>
      </div>
    </aside>
  );
}
