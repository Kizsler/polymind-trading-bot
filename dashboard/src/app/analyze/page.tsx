"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { PnLChart, EquityChart } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Home,
  ChevronRight,
  BarChart3,
  TrendingUp,
  Target,
  Percent,
} from "lucide-react";

// Generate sample data
const generatePnLData = () => {
  const data = [];
  const now = new Date();
  for (let i = 30; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
      pnl: Math.random() * 15 - 5,
    });
  }
  return data;
};

const generateEquityData = () => {
  const data = [];
  const now = new Date();
  let equity = 1000;
  for (let i = 30; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    equity += Math.random() * 80 - 25;
    data.push({
      date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
      equity: Math.max(equity, 500),
    });
  }
  return data;
};

export default function AnalyzePage() {
  const pnlData = generatePnLData();
  const equityData = generateEquityData();

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8 animate-fade-in">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Analyze</span>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <h1 className="text-2xl font-display font-bold flex items-center gap-3">
          <BarChart3 className="h-6 w-6 text-violet-400" />
          Performance Analysis
        </h1>
        <p className="text-muted-foreground mt-1">
          Detailed metrics and performance tracking
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4 mb-8 animate-fade-in stagger-2">
        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Total Return
              </p>
            </div>
            <p className="text-2xl font-mono font-bold text-emerald-400">
              +12.4%
            </p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-violet-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Win Rate
              </p>
            </div>
            <p className="text-2xl font-mono font-bold">
              62.5%
            </p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Percent className="h-4 w-4 text-cyan-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Profit Factor
              </p>
            </div>
            <p className="text-2xl font-mono font-bold">
              1.85
            </p>
          </CardContent>
        </Card>

        <Card className="glass border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="h-4 w-4 text-fuchsia-400" />
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Max Drawdown
              </p>
            </div>
            <p className="text-2xl font-mono font-bold text-red-400">
              -8.2%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="space-y-6">
        <div className="animate-fade-in stagger-3">
          <PnLChart data={pnlData} title="Daily Returns (%)" />
        </div>

        <div className="animate-fade-in stagger-4">
          <EquityChart data={equityData} title="Portfolio Value" />
        </div>
      </div>
    </ThreeColumnLayout>
  );
}
