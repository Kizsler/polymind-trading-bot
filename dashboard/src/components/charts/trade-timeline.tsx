"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

// Get singleton client outside component
const supabase = createClient();

interface Trade {
  id: number;
  market_id: string;
  market_title?: string;
  wallet: string;
  wallet_alias?: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  executed: boolean;
  timestamp: string;
}

interface TimelinePoint {
  time: number;
  size: number;
  side: "YES" | "NO";
  price: number;
  market: string;
  wallet: string;
  displayTime: string;
}

export function TradeTimeline() {
  const { user, profile, loading: authLoading } = useAuth();
  const [trades, setTrades] = useState<Trade[]>([]);

  const fetchTrades = useCallback(async () => {
    if (!user) return;

    const { data } = await supabase
      .from("trades")
      .select("*")
      .eq("user_id", user.id)
      .eq("executed", true)
      .order("timestamp", { ascending: false })
      .limit(100);

    if (data) setTrades(data);
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) return;

    fetchTrades();

    // Subscribe to realtime updates for this user's trades
    const channel = supabase
      .channel(`timeline-trades-${user.id}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "trades",
          filter: `user_id=eq.${user.id}`
        },
        () => {
          fetchTrades();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, authLoading, fetchTrades]);

  const copyPercentage = profile?.copy_percentage || 0.1;

  // Transform trades into timeline data
  const timelineData = useMemo(() => {
    if (!trades || trades.length === 0) return [];

    return trades
      .map((trade) => {
        const date = new Date(trade.timestamp);
        return {
          time: date.getTime(),
          size: trade.size * copyPercentage,
          side: trade.side,
          price: trade.price,
          market: trade.market_title || trade.market_id.slice(0, 15) + "...",
          wallet: trade.wallet_alias || trade.wallet.slice(0, 8) + "...",
          displayTime: date.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
          }),
        };
      })
      .sort((a, b) => a.time - b.time)
      .slice(-50); // Last 50 trades
  }, [trades, copyPercentage]);

  // Get time bounds for x-axis
  const timeBounds = useMemo(() => {
    if (timelineData.length === 0) {
      const now = Date.now();
      return { min: now - 3600000, max: now };
    }
    const times = timelineData.map((d) => d.time);
    const min = Math.min(...times);
    const max = Math.max(...times);
    const padding = (max - min) * 0.1 || 3600000;
    return { min: min - padding, max: max + padding };
  }, [timelineData]);

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: TimelinePoint }> }) => {
    if (!active || !payload || !payload[0]) return null;
    const data = payload[0].payload;

    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{data.displayTime}</p>
        <p className="text-sm font-medium text-white mb-1">{data.market}</p>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              data.side === "YES"
                ? "bg-emerald-500/20 text-emerald-400"
                : "bg-red-500/20 text-red-400"
            }`}
          >
            {data.side}
          </span>
          <span className="text-sm text-white font-mono">${data.size.toFixed(2)}</span>
          <span className="text-xs text-slate-400">@ {data.price.toFixed(2)}</span>
        </div>
        <p className="text-xs text-slate-500 mt-1">From: {data.wallet}</p>
      </div>
    );
  };

  return (
    <Card className="glass border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-display flex items-center gap-2">
            <Activity className="h-5 w-5 text-violet-400" />
            Trade Timeline
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Last {timelineData.length} trades
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-48">
          {timelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis
                  type="number"
                  dataKey="time"
                  domain={[timeBounds.min, timeBounds.max]}
                  tickFormatter={formatTime}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                />
                <YAxis
                  type="number"
                  dataKey="size"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="#334155" />
                <Scatter data={timelineData} shape="circle">
                  {timelineData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.side === "YES" ? "#10b981" : "#ef4444"}
                      fillOpacity={0.7}
                      r={Math.min(Math.max(entry.size / 2, 4), 12)}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              No trades yet
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
