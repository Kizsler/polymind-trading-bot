"use client";

import { useMemo, useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Trophy,
  Target,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface Trade {
  wallet: string;
  wallet_alias?: string;
  side: "YES" | "NO";
  size: number;
  price: number;
}

interface WalletStats {
  address: string;
  alias: string;
  tradeCount: number;
  totalVolume: number;
  yesCount: number;
  noCount: number;
  avgPrice: number;
  contribution: number;
}

export function WalletPerformance() {
  const { user, profile } = useAuth();
  const supabase = createClient();
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    const fetchTrades = async () => {
      if (!user) return;

      const { data } = await supabase
        .from("trades")
        .select("wallet, wallet_alias, side, size, price")
        .eq("user_id", user.id)
        .eq("executed", true)
        .order("timestamp", { ascending: false })
        .limit(500);

      if (data) setTrades(data);
    };

    fetchTrades();
  }, [user, supabase]);

  const copyPercentage = profile?.copy_percentage || 0.1;

  // Calculate wallet stats from trades
  const walletStats = useMemo(() => {
    if (!trades || trades.length === 0) return [];

    const statsMap = new Map<string, WalletStats>();
    let totalVolume = 0;

    // Aggregate trades
    trades.forEach((trade) => {
      const walletKey = trade.wallet.toLowerCase();
      const existing = statsMap.get(walletKey);
      const tradeVolume = trade.size * copyPercentage;
      totalVolume += tradeVolume;

      if (existing) {
        const newTotal = existing.totalVolume + tradeVolume;
        statsMap.set(walletKey, {
          ...existing,
          tradeCount: existing.tradeCount + 1,
          totalVolume: newTotal,
          yesCount: existing.yesCount + (trade.side === "YES" ? 1 : 0),
          noCount: existing.noCount + (trade.side === "NO" ? 1 : 0),
          avgPrice:
            (existing.avgPrice * existing.tradeCount + trade.price) /
            (existing.tradeCount + 1),
        });
      } else {
        statsMap.set(walletKey, {
          address: trade.wallet,
          alias: trade.wallet_alias || trade.wallet.slice(0, 10) + "...",
          tradeCount: 1,
          totalVolume: tradeVolume,
          yesCount: trade.side === "YES" ? 1 : 0,
          noCount: trade.side === "NO" ? 1 : 0,
          avgPrice: trade.price,
          contribution: 0,
        });
      }
    });

    // Calculate contribution percentages
    return Array.from(statsMap.values())
      .map((stats) => ({
        ...stats,
        contribution: totalVolume > 0 ? (stats.totalVolume / totalVolume) * 100 : 0,
      }))
      .filter((s) => s.tradeCount > 0)
      .sort((a, b) => b.totalVolume - a.totalVolume);
  }, [trades, copyPercentage]);

  const topPerformer = walletStats[0];

  return (
    <Card className="glass border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-display flex items-center gap-2">
            <Users className="h-5 w-5 text-violet-400" />
            Wallet Performance
          </CardTitle>
          {topPerformer && (
            <div className="flex items-center gap-1 text-xs text-amber-400">
              <Trophy className="h-3.5 w-3.5" />
              <span>{topPerformer.alias}</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {walletStats.length > 0 ? (
          <div className="space-y-4">
            {walletStats.map((wallet, i) => {
              const yesPct =
                wallet.tradeCount > 0
                  ? (wallet.yesCount / wallet.tradeCount) * 100
                  : 0;
              const isTop = i === 0;

              return (
                <div
                  key={wallet.address}
                  className={`p-3 rounded-lg ${
                    isTop ? "bg-amber-500/5 border border-amber-500/20" : "bg-secondary/30"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {isTop && <Trophy className="h-4 w-4 text-amber-400" />}
                      <span className="font-medium text-sm">{wallet.alias}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-xs">
                        {wallet.tradeCount} trades
                      </Badge>
                      <span className="text-sm font-mono text-emerald-400">
                        ${wallet.totalVolume.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3 text-emerald-500" />
                      <span>{wallet.yesCount} YES</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <TrendingDown className="h-3 w-3 text-red-500" />
                      <span>{wallet.noCount} NO</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Target className="h-3 w-3 text-violet-400" />
                      <span>Avg: ${wallet.avgPrice.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* YES/NO ratio bar */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-emerald-400 w-8">
                      {yesPct.toFixed(0)}%
                    </span>
                    <div className="flex-1 h-1.5 rounded-full bg-red-500/30 overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all duration-300"
                        style={{ width: `${yesPct}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-red-400 w-8 text-right">
                      {(100 - yesPct).toFixed(0)}%
                    </span>
                  </div>

                  {/* Contribution bar */}
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                      <span>Volume contribution</span>
                      <span>{wallet.contribution.toFixed(1)}%</span>
                    </div>
                    <Progress value={wallet.contribution} className="h-1" />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-muted-foreground py-8">
            No wallet activity yet
          </p>
        )}
      </CardContent>
    </Card>
  );
}
