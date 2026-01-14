"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Bot,
  RefreshCw,
  Clock,
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertCircle,
  Brain,
  ShieldCheck,
  Target,
  Zap,
} from "lucide-react";
import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface AIEvaluation {
  id: string;
  user_id: string;
  trade_id: number;
  action: "HOLD" | "SELL";
  reasoning: string;
  confidence: number;
  signals: {
    position: {
      market_id: string;
      market_title?: string;
      side: string;
      size: number;
      entry_price: number;
      current_price: number;
      unrealized_pnl: number;
      hold_duration_hours: number;
    };
    market: {
      resolution_date?: string;
      volume_24h?: number;
      liquidity?: number;
    };
    whale: {
      still_holding: boolean;
      whale_alias?: string;
    };
  };
  strategy_used: "conservative" | "moderate" | "aggressive" | "maximize_profit";
  created_at: string;
}

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

function getStrategyIcon(strategy: string) {
  switch (strategy) {
    case "conservative":
      return <ShieldCheck className="h-4 w-4" />;
    case "moderate":
      return <Target className="h-4 w-4" />;
    case "aggressive":
      return <Zap className="h-4 w-4" />;
    case "maximize_profit":
      return <TrendingUp className="h-4 w-4" />;
    default:
      return <Brain className="h-4 w-4" />;
  }
}

function getStrategyColor(strategy: string) {
  switch (strategy) {
    case "conservative":
      return "text-blue-400 border-blue-400/30 bg-blue-400/10";
    case "moderate":
      return "text-yellow-400 border-yellow-400/30 bg-yellow-400/10";
    case "aggressive":
      return "text-orange-400 border-orange-400/30 bg-orange-400/10";
    case "maximize_profit":
      return "text-profit border-profit/30 bg-profit/10";
    default:
      return "text-muted-foreground";
  }
}

export default function AILogPage() {
  const [evaluations, setEvaluations] = useState<AIEvaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("all");

  const supabase = createClient();

  const fetchEvaluations = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, error: fetchError } = await supabase
        .from("ai_evaluations")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(100);

      if (fetchError) throw fetchError;
      setEvaluations(data || []);
    } catch (err) {
      console.error("Failed to fetch AI evaluations:", err);
      setError("Failed to load AI evaluations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvaluations();
  }, []);

  const filteredEvaluations = evaluations.filter((eval_) => {
    if (activeTab === "all") return true;
    if (activeTab === "sell") return eval_.action === "SELL";
    if (activeTab === "hold") return eval_.action === "HOLD";
    return true;
  });

  const stats = {
    total: evaluations.length,
    sells: evaluations.filter((e) => e.action === "SELL").length,
    holds: evaluations.filter((e) => e.action === "HOLD").length,
    avgConfidence:
      evaluations.length > 0
        ? evaluations.reduce((acc, e) => acc + e.confidence, 0) / evaluations.length
        : 0,
  };

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <Bot className="h-8 w-8 text-violet-400" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight">AI Decision Log</h1>
              <p className="text-muted-foreground mt-1">
                View all AI evaluations and reasoning for position management
              </p>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">Error Loading Data</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums flex items-center gap-2">
                <Brain className="h-5 w-5 text-violet-400" />
                {stats.total}
              </div>
              <p className="text-sm text-muted-foreground">Total Evaluations</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums text-amber-400">
                {stats.sells}
              </div>
              <p className="text-sm text-muted-foreground">Sell Decisions</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums text-blue-400">
                {stats.holds}
              </div>
              <p className="text-sm text-muted-foreground">Hold Decisions</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold tabular-nums text-profit">
                {(stats.avgConfidence * 100).toFixed(0)}%
              </div>
              <p className="text-sm text-muted-foreground">Avg Confidence</p>
            </CardContent>
          </Card>
        </div>

        {/* Evaluations List */}
        <Card className="bg-card border-border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Evaluation History</CardTitle>
              <Button
                variant="outline"
                size="icon"
                onClick={fetchEvaluations}
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-4">
              <TabsList className="bg-secondary">
                <TabsTrigger value="all">All ({stats.total})</TabsTrigger>
                <TabsTrigger value="sell">
                  <TrendingDown className="h-3 w-3 mr-1" />
                  Sells ({stats.sells})
                </TabsTrigger>
                <TabsTrigger value="hold">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Holds ({stats.holds})
                </TabsTrigger>
              </TabsList>
            </Tabs>

            {/* Loading State */}
            {loading && evaluations.length === 0 && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading evaluations...</span>
              </div>
            )}

            {/* Evaluations */}
            <div className="space-y-4">
              {filteredEvaluations.map((eval_) => (
                <div
                  key={eval_.id}
                  className="border border-border rounded-lg p-4 hover:bg-secondary/30 transition-colors"
                >
                  {/* Header Row */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <Badge
                        variant="outline"
                        className={
                          eval_.action === "SELL"
                            ? "text-amber-400 border-amber-400/30 bg-amber-400/10"
                            : "text-blue-400 border-blue-400/30 bg-blue-400/10"
                        }
                      >
                        {eval_.action === "SELL" ? (
                          <TrendingDown className="h-3 w-3 mr-1" />
                        ) : (
                          <TrendingUp className="h-3 w-3 mr-1" />
                        )}
                        {eval_.action}
                      </Badge>
                      <Badge variant="outline" className={getStrategyColor(eval_.strategy_used)}>
                        {getStrategyIcon(eval_.strategy_used)}
                        <span className="ml-1 capitalize">{eval_.strategy_used.replace("_", " ")}</span>
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        Confidence: <span className="text-foreground font-medium">{(eval_.confidence * 100).toFixed(0)}%</span>
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground text-sm">
                      <Clock className="h-3 w-3" />
                      {formatTime(eval_.created_at)}
                    </div>
                  </div>

                  {/* Market Info */}
                  <div className="mb-3">
                    <p className="text-sm font-medium truncate">
                      {eval_.signals.position.market_title || eval_.signals.position.market_id}
                    </p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span>
                        Side: <span className={eval_.signals.position.side === "YES" ? "text-profit" : "text-loss"}>{eval_.signals.position.side}</span>
                      </span>
                      <span>Size: ${eval_.signals.position.size.toFixed(2)}</span>
                      <span>Entry: {eval_.signals.position.entry_price.toFixed(4)}</span>
                      <span>Current: {eval_.signals.position.current_price.toFixed(4)}</span>
                      <span className={eval_.signals.position.unrealized_pnl >= 0 ? "text-profit" : "text-loss"}>
                        P&L: {eval_.signals.position.unrealized_pnl >= 0 ? "+" : ""}${eval_.signals.position.unrealized_pnl.toFixed(2)}
                      </span>
                      <span>Hold: {eval_.signals.position.hold_duration_hours.toFixed(1)}h</span>
                    </div>
                  </div>

                  {/* Reasoning */}
                  <div className="bg-secondary/50 rounded-md p-3">
                    <div className="flex items-start gap-2">
                      <Bot className="h-4 w-4 text-violet-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-violet-400 mb-1">AI Reasoning</p>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{eval_.reasoning}</p>
                      </div>
                    </div>
                  </div>

                  {/* Signals Summary */}
                  <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                    <span>
                      Whale: {eval_.signals.whale.still_holding ? (
                        <span className="text-profit">Still Holding</span>
                      ) : (
                        <span className="text-loss">Exited</span>
                      )}
                      {eval_.signals.whale.whale_alias && ` (${eval_.signals.whale.whale_alias})`}
                    </span>
                    {eval_.signals.market.resolution_date && (
                      <span>
                        Resolves: {new Date(eval_.signals.market.resolution_date).toLocaleDateString()}
                      </span>
                    )}
                    {eval_.signals.market.volume_24h && (
                      <span>24h Vol: ${(eval_.signals.market.volume_24h / 1000).toFixed(1)}k</span>
                    )}
                  </div>
                </div>
              ))}

              {filteredEvaluations.length === 0 && !loading && (
                <div className="text-center py-12 text-muted-foreground">
                  <Bot className="h-12 w-12 mx-auto mb-4 opacity-30" />
                  <p>No AI evaluations yet.</p>
                  <p className="text-sm mt-1">
                    Evaluations will appear here when the AI analyzes your positions.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
