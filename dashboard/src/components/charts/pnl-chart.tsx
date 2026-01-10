"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PnLChartProps {
  data: Array<{ date: string; pnl: number }>;
  title?: string;
}

export function PnLChart({ data, title = "ROI (%)" }: PnLChartProps) {
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
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "#f8fafc" }}
                formatter={(value) => [`${Number(value).toFixed(2)}%`, "ROI"]}
              />
              <Bar
                dataKey="pnl"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.pnl >= 0 ? "#7c3aed" : "#ef4444"}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
