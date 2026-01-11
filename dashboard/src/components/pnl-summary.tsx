"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  RefreshCw,
  Trophy,
  Target,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface Trade {
  id: number;
  market_id: string;
  market_title?: string;
  side: string;
  pnl?: number;
  executed: boolean;
}

export function PnLSummary() {
  const { user, profile } = useAuth();
  const supabase = createClient();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTrades = async () => {
    if (!user) return;
    setLoading(true);

    const { data } = await supabase
      .from("trades")
      .select("id, market_id, market_title, side, pnl, executed")
      .eq("user_id", user.id)
      .order("timestamp", { ascending: false });

    if (data) setTrades(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchTrades();
  }, [user]);

  // Calculate PnL from trades
  const pnlData = useMemo(() => {
    const executedTrades = trades.filter(t => t.executed && t.pnl !== null && t.pnl !== undefined);

    const wins = executedTrades.filter(t => (t.pnl || 0) > 0);
    const losses = executedTrades.filter(t => (t.pnl || 0) < 0);

    const totalPnl = executedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalWon = wins.reduce((sum, t) => sum + (t.pnl || 0), 0);
    const totalLost = losses.reduce((sum, t) => sum + (t.pnl || 0), 0);

    const winRate = executedTrades.length > 0
      ? ((wins.length / executedTrades.length) * 100).toFixed(1)
      : "0.0";

    return {
      total_pnl: totalPnl.toFixed(2),
      win_count: wins.length,
      loss_count: losses.length,
      win_rate: winRate,
      total_won: totalWon.toFixed(2),
      total_lost: totalLost.toFixed(2),
      details: executedTrades.slice(0, 10).map(t => ({
        id: t.id.toString(),
        pnl: t.pnl || 0,
        market: t.market_title || t.market_id.slice(0, 30),
        side: t.side,
        won: (t.pnl || 0) > 0,
      })),
    };
  }, [trades]);

  const totalPnl = parseFloat(pnlData.total_pnl);
  const isProfitable = totalPnl > 0;
  const startingBalance = profile?.starting_balance || 1000;

  return (
    <Card className="glass border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-display flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-violet-400" />
            Performance Summary
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchTrades}
            disabled={loading}
            className="h-8 px-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && trades.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Starting Balance */}
            <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Starting Balance</span>
                <span className="text-lg font-mono font-bold text-violet-400">
                  ${startingBalance.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Main PnL Display */}
            <div className={`p-4 rounded-lg ${isProfitable ? "bg-emerald-500/10 border border-emerald-500/20" : totalPnl < 0 ? "bg-red-500/10 border border-red-500/20" : "bg-secondary/30 border border-border"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isProfitable ? (
                    <TrendingUp className="h-6 w-6 text-emerald-400" />
                  ) : totalPnl < 0 ? (
                    <TrendingDown className="h-6 w-6 text-red-400" />
                  ) : (
                    <DollarSign className="h-6 w-6 text-muted-foreground" />
                  )}
                  <span className="text-sm text-muted-foreground">Total P&L</span>
                </div>
                <span className={`text-2xl font-mono font-bold ${isProfitable ? "text-emerald-400" : totalPnl < 0 ? "text-red-400" : "text-muted-foreground"}`}>
                  {isProfitable ? "+" : ""}${pnlData.total_pnl}
                </span>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-secondary/30">
                <div className="flex items-center gap-2 mb-1">
                  <Trophy className="h-4 w-4 text-amber-400" />
                  <span className="text-xs text-muted-foreground">Win Rate</span>
                </div>
                <span className="text-lg font-mono font-semibold">{pnlData.win_rate}%</span>
              </div>

              <div className="p-3 rounded-lg bg-secondary/30">
                <div className="flex items-center gap-2 mb-1">
                  <Target className="h-4 w-4 text-violet-400" />
                  <span className="text-xs text-muted-foreground">Total Trades</span>
                </div>
                <span className="text-lg font-mono font-semibold">{pnlData.win_count + pnlData.loss_count}</span>
              </div>

              <div className="p-3 rounded-lg bg-emerald-500/5">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  <span className="text-xs text-muted-foreground">Wins</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-mono font-semibold text-emerald-400">{pnlData.win_count}</span>
                  <span className="text-xs font-mono text-emerald-400">+${pnlData.total_won}</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-red-500/5">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingDown className="h-4 w-4 text-red-500" />
                  <span className="text-xs text-muted-foreground">Losses</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-mono font-semibold text-red-400">{pnlData.loss_count}</span>
                  <span className="text-xs font-mono text-red-400">${pnlData.total_lost}</span>
                </div>
              </div>
            </div>

            {/* Recent Trades */}
            {pnlData.details && pnlData.details.length > 0 && (
              <div className="pt-2">
                <p className="text-xs text-muted-foreground mb-2">Recent Resolved Trades</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {pnlData.details.map((trade, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-border/30 last:border-0">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${trade.won ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"}`}
                        >
                          {trade.won ? "W" : "L"}
                        </Badge>
                        <span className="truncate text-muted-foreground">{trade.market}</span>
                      </div>
                      <span className={`font-mono ${trade.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {trades.length === 0 && (
              <p className="text-center text-muted-foreground text-sm py-4">
                No trades yet. Your bot will start trading when wallets you follow make moves.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
