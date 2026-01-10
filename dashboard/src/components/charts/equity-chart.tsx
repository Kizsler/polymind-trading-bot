"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface EquityChartProps {
  data: Array<{ date: string; equity: number }>;
  title?: string;
}

export function EquityChart({ data, title = "Equity" }: EquityChartProps) {
  return (
    <Card className="glass border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-display">{title}</CardTitle>
          <div className="flex gap-1">
            {["1W", "1M", "6M", "1Y"].map((period) => (
              <button
                key={period}
                className="px-2 py-1 text-xs rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
              >
                {period}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.4} />
                  <stop offset="50%" stopColor="#d946ef" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#d946ef" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="equityStroke" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7c3aed" />
                  <stop offset="100%" stopColor="#d946ef" />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#64748b", fontSize: 10 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#64748b", fontSize: 10 }}
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "#f8fafc" }}
                formatter={(value) => [`$${Number(value).toFixed(2)}`, "Equity"]}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="url(#equityStroke)"
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
