"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Home,
  ChevronRight,
  Brain,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import useSWR from "swr";
import { fetcher, Trade } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AlgoPage() {
  const { data: trades } = useSWR<Trade[]>("/trades?limit=50", fetcher, {
    refreshInterval: 10000
  });

  const decisions = trades?.filter(t => t.decision) || [];
  const copied = decisions.filter(t => t.decision === "COPY").length;
  const skipped = decisions.filter(t => t.decision === "SKIP").length;

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8 animate-fade-in">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Algo</span>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <h1 className="text-2xl font-display font-bold flex items-center gap-3">
          <Brain className="h-6 w-6 text-violet-400" />
          AI Decision Engine
        </h1>
        <p className="text-muted-foreground mt-1">
          Claude-powered trade analysis and execution decisions
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3 mb-8 animate-fade-in stagger-2">
        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Total Decisions
                </p>
                <p className="text-3xl font-mono font-bold mt-1">
                  {decisions.length}
                </p>
              </div>
              <Brain className="h-8 w-8 text-violet-400 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Copied
                </p>
                <p className="text-3xl font-mono font-bold mt-1 text-emerald-400">
                  {copied}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Skipped
                </p>
                <p className="text-3xl font-mono font-bold mt-1 text-red-400">
                  {skipped}
                </p>
              </div>
              <XCircle className="h-8 w-8 text-red-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decision History */}
      <Card className="glass border-border animate-fade-in stagger-3">
        <CardHeader>
          <CardTitle className="text-lg font-display">Decision History</CardTitle>
        </CardHeader>
        <CardContent>
          {decisions.length > 0 ? (
            <div className="space-y-3">
              {decisions.map((trade, i) => (
                <div
                  key={trade.id || i}
                  className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-border/50"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "h-10 w-10 rounded-lg flex items-center justify-center",
                      trade.decision === "COPY" ? "bg-emerald-500/10" :
                      trade.decision === "SKIP" ? "bg-red-500/10" : "bg-yellow-500/10"
                    )}>
                      {trade.decision === "COPY" ? (
                        <CheckCircle className="h-5 w-5 text-emerald-400" />
                      ) : trade.decision === "SKIP" ? (
                        <XCircle className="h-5 w-5 text-red-400" />
                      ) : (
                        <Clock className="h-5 w-5 text-yellow-400" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">
                        {trade.market_title || trade.market_id.slice(0, 30) + "..."}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {trade.wallet_alias || trade.wallet.slice(0, 10)} • {trade.side} • ${trade.size.toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      trade.decision === "COPY" ? "border-emerald-500/30 text-emerald-400" :
                      trade.decision === "SKIP" ? "border-red-500/30 text-red-400" :
                      "border-yellow-500/30 text-yellow-400"
                    )}
                  >
                    {trade.decision}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No AI decisions yet. Start tracking wallets to see decisions.
            </p>
          )}
        </CardContent>
      </Card>
    </ThreeColumnLayout>
  );
}
