"use client";

import { useMemo, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  TrendingUp,
  TrendingDown,
  Layers,
  DollarSign,
  Clock,
  Calendar,
} from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface Trade {
  id: number;
  market_id: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  executed: boolean;
}

interface Market {
  condition_id: string;
  question: string;
  description: string;
  end_date: string | null;
  resolution_date: string | null;
  active: boolean;
  closed: boolean;
}

interface Position {
  market_id: string;
  side: "YES" | "NO";
  total_size: number;
  avg_price: number;
  trade_count: number;
  current_exposure: number;
}

interface PositionWithMarket extends Position {
  market?: Market;
}

// Format relative time
function formatTimeUntil(dateStr: string | null | undefined): string {
  if (!dateStr) return "No end date";

  const endDate = new Date(dateStr);
  const now = new Date();
  const diff = endDate.getTime() - now.getTime();

  if (diff < 0) return "Ended";

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

  if (days > 30) {
    const months = Math.floor(days / 30);
    return `${months} month${months > 1 ? 's' : ''}`;
  }
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h`;

  const minutes = Math.floor(diff / (1000 * 60));
  return `${minutes}m`;
}

// Format end date for display
function formatEndDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "TBD";

  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined,
  });
}

export function PositionsBreakdown() {
  const { user, profile } = useAuth();
  const supabase = createClient();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [marketData, setMarketData] = useState<Record<string, Market>>({});

  useEffect(() => {
    const fetchTrades = async () => {
      if (!user) return;

      const { data } = await supabase
        .from("trades")
        .select("id, market_id, side, size, price, executed")
        .eq("user_id", user.id)
        .eq("executed", true)
        .order("timestamp", { ascending: false })
        .limit(500);

      if (data) setTrades(data);
    };

    fetchTrades();
  }, [user, supabase]);

  const copyPercentage = profile?.copy_percentage || 0.1;

  // Aggregate trades into positions by market
  const positions = useMemo(() => {
    if (!trades) return [];

    const positionMap = new Map<string, Position>();

    trades.forEach((trade) => {
      const key = `${trade.market_id}-${trade.side}`;
      const existing = positionMap.get(key);
      const tradeSize = trade.size * copyPercentage;

      if (existing) {
        const newTotalSize = existing.total_size + tradeSize;
        const newAvgPrice =
          (existing.avg_price * existing.total_size + trade.price * tradeSize) /
          newTotalSize;

        positionMap.set(key, {
          ...existing,
          total_size: newTotalSize,
          avg_price: newAvgPrice,
          trade_count: existing.trade_count + 1,
          current_exposure: newTotalSize,
        });
      } else {
        positionMap.set(key, {
          market_id: trade.market_id,
          side: trade.side,
          total_size: tradeSize,
          avg_price: trade.price,
          trade_count: 1,
          current_exposure: tradeSize,
        });
      }
    });

    // Convert to array and sort by exposure
    return Array.from(positionMap.values())
      .sort((a, b) => b.current_exposure - a.current_exposure)
      .slice(0, 10); // Top 10 positions
  }, [trades, copyPercentage]);

  // Fetch market metadata via Next.js API route (proxies to Gamma API)
  useEffect(() => {
    const fetchMarkets = async () => {
      const uniqueMarketIds = [...new Set(positions.map((p) => p.market_id))];
      const missingIds = uniqueMarketIds.filter((id) => !marketData[id]);

      if (missingIds.length === 0) return;

      // Fetch each market via our API route
      const newData: Record<string, Market> = {};

      await Promise.all(
        missingIds.slice(0, 10).map(async (marketId) => {
          try {
            const response = await fetch(`/api/markets/${encodeURIComponent(marketId)}`);
            if (response.ok) {
              const data = await response.json();
              newData[marketId] = data;
            }
          } catch {
            // If fetch fails, use a fallback
            newData[marketId] = {
              condition_id: marketId,
              question: marketId.slice(0, 30) + "...",
              description: "",
              end_date: null,
              resolution_date: null,
              active: true,
              closed: false,
            };
          }
        })
      );

      if (Object.keys(newData).length > 0) {
        setMarketData((prev) => ({ ...prev, ...newData }));
      }
    };

    if (positions.length > 0) {
      fetchMarkets();
    }
  }, [positions, marketData]);

  // Combine positions with market data
  const positionsWithMarkets: PositionWithMarket[] = positions.map((pos) => ({
    ...pos,
    market: marketData[pos.market_id],
  }));

  const totalExposure = positions.reduce((sum, p) => sum + p.current_exposure, 0);

  return (
    <Card className="glass border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-display flex items-center gap-2">
            <Layers className="h-5 w-5 text-violet-400" />
            Open Positions
          </CardTitle>
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-mono text-emerald-400">
              ${totalExposure.toFixed(2)}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {positionsWithMarkets.length > 0 ? (
          <div className="space-y-4">
            {positionsWithMarkets.map((position, i) => {
              const exposurePercent = (position.current_exposure / totalExposure) * 100;
              const marketTitle = position.market?.question || position.market_id.slice(0, 30) + "...";
              const endDate = position.market?.end_date;
              const timeUntil = formatTimeUntil(endDate);
              const isEnding = endDate && new Date(endDate).getTime() - Date.now() < 24 * 60 * 60 * 1000;

              return (
                <div key={i} className="space-y-2 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                  {/* Market title and side */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      <div
                        className={`h-6 w-6 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${
                          position.side === "YES"
                            ? "bg-emerald-500/10"
                            : "bg-red-500/10"
                        }`}
                      >
                        {position.side === "YES" ? (
                          <TrendingUp className="h-3 w-3 text-emerald-500" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-red-500" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium leading-tight" title={position.market?.question || position.market_id}>
                          {marketTitle}
                        </p>
                        {/* End date row */}
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{formatEndDate(endDate)}</span>
                          </div>
                          <span className="text-border">•</span>
                          <div className={`flex items-center gap-1 ${isEnding ? 'text-amber-400' : ''}`}>
                            <Clock className="h-3 w-3" />
                            <span>{timeUntil}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1 flex-shrink-0">
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          position.side === "YES"
                            ? "border-emerald-500/30 text-emerald-400"
                            : "border-red-500/30 text-red-400"
                        }`}
                      >
                        {position.side}
                      </Badge>
                      <span className="text-sm font-mono font-semibold text-emerald-400">
                        ${position.current_exposure.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Stats and progress */}
                  <div className="flex items-center gap-3 mt-2">
                    <Progress
                      value={exposurePercent}
                      className="h-1.5 flex-1"
                    />
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>Avg: ${position.avg_price.toFixed(2)}</span>
                      <span className="text-border">|</span>
                      <span>{position.trade_count} trade{position.trade_count > 1 ? 's' : ''}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-muted-foreground py-8">
            No open positions
          </p>
        )}
      </CardContent>
    </Card>
  );
}
