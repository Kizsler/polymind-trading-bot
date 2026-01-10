# PolyMind Dashboard Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the PolyMind dashboard with a distinctive dark trading aesthetic, real-time crypto prices, and three-column layout matching the reference design.

**Architecture:** Next.js 14 App Router with shadcn/ui components, Recharts for data visualization, CoinGecko API for live crypto prices, WebSocket for real-time trade updates. Three-column layout: navigation sidebar, main content area, status panel.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui, Recharts, CoinGecko API

---

## Design Direction

**Aesthetic:** "Midnight Terminal" - A refined, dark trading interface that feels like a high-end Bloomberg terminal meets modern web design. Not generic fintech purple-on-white.

**Typography:**
- Display: "JetBrains Mono" for numbers/data (monospace precision)
- Headers: "Sora" (geometric, modern, distinctive)
- Body: "DM Sans" (clean, readable)

**Color Palette:**
```css
--background: #0a0e17;        /* Deep midnight */
--card: #111827;              /* Slightly lifted */
--card-hover: #1a2234;        /* Interactive state */
--border: #1e293b;            /* Subtle edges */
--accent-violet: #7c3aed;     /* Primary accent */
--accent-fuchsia: #d946ef;    /* Secondary/gradients */
--accent-cyan: #06b6d4;       /* Tertiary highlights */
--profit: #10b981;            /* Green for gains */
--loss: #ef4444;              /* Red for losses */
--text-primary: #f8fafc;      /* Bright white */
--text-muted: #64748b;        /* Subdued gray */
```

**Signature Elements:**
- Gradient glow effects on charts (violet → fuchsia)
- Subtle grid pattern overlay on backgrounds
- Glassmorphism on cards (backdrop-blur)
- Staggered fade-in animations on page load
- Pulsing dot for "live" indicators

---

## Task 1: Install Dependencies & Setup Fonts

**Files:**
- Modify: `dashboard/package.json`
- Modify: `dashboard/src/app/layout.tsx`
- Modify: `dashboard/tailwind.config.ts`

**Step 1: Install recharts**

Run:
```bash
cd dashboard && npm install recharts
```

**Step 2: Add Google Fonts to layout.tsx**

Modify `dashboard/src/app/layout.tsx`:
```tsx
import { Sora, DM_Sans, JetBrains_Mono } from "next/font/google";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

// In the html tag:
<html lang="en" className={`dark ${sora.variable} ${dmSans.variable} ${jetbrains.variable}`}>
```

**Step 3: Update Tailwind config**

Modify `dashboard/tailwind.config.ts` to add font families:
```ts
fontFamily: {
  sans: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
  display: ["var(--font-sora)", "system-ui", "sans-serif"],
  mono: ["var(--font-mono)", "monospace"],
},
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add recharts and custom fonts"
```

---

## Task 2: Update Global Styles & CSS Variables

**Files:**
- Modify: `dashboard/src/app/globals.css`

**Step 1: Replace CSS variables with new palette**

Update `dashboard/src/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222 47% 6%;
    --foreground: 210 40% 98%;
    --card: 222 47% 9%;
    --card-foreground: 210 40% 98%;
    --popover: 222 47% 9%;
    --popover-foreground: 210 40% 98%;
    --primary: 263 70% 58%;
    --primary-foreground: 210 40% 98%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 50%;
    --accent: 263 70% 58%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 263 70% 58%;
    --radius: 0.75rem;

    /* Custom colors */
    --profit: 160 84% 39%;
    --loss: 0 84% 60%;
    --violet: 263 70% 58%;
    --fuchsia: 292 84% 61%;
    --cyan: 188 94% 43%;
  }

  .dark {
    --background: 222 47% 6%;
    --foreground: 210 40% 98%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
  }
}

/* Custom utility classes */
@layer utilities {
  .text-profit {
    @apply text-emerald-500;
  }
  .text-loss {
    @apply text-red-500;
  }
  .bg-profit {
    @apply bg-emerald-500;
  }
  .bg-loss {
    @apply bg-red-500;
  }
  .font-display {
    font-family: var(--font-sora), system-ui, sans-serif;
  }
  .font-mono-data {
    font-family: var(--font-mono), monospace;
  }
  .glow-violet {
    box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
  }
  .glow-profit {
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
  }
  .gradient-violet {
    background: linear-gradient(135deg, #7c3aed 0%, #d946ef 100%);
  }
  .glass {
    @apply bg-card/80 backdrop-blur-xl border border-white/5;
  }
}

/* Grid pattern background */
.bg-grid {
  background-image:
    linear-gradient(rgba(124, 58, 237, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124, 58, 237, 0.03) 1px, transparent 1px);
  background-size: 32px 32px;
}

/* Animations */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse-live {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-fade-in {
  animation: fade-in 0.5s ease-out forwards;
}

.animate-pulse-live {
  animation: pulse-live 2s ease-in-out infinite;
}

.stagger-1 { animation-delay: 0.1s; }
.stagger-2 { animation-delay: 0.2s; }
.stagger-3 { animation-delay: 0.3s; }
.stagger-4 { animation-delay: 0.4s; }
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): update global styles with midnight terminal theme"
```

---

## Task 3: Create Three-Column Layout Component

**Files:**
- Create: `dashboard/src/components/layouts/three-column-layout.tsx`

**Step 1: Create the layout component**

Create `dashboard/src/components/layouts/three-column-layout.tsx`:
```tsx
"use client";

import { ReactNode } from "react";
import { Sidebar } from "@/components/sidebar-new";
import { StatusPanel } from "@/components/status-panel";

interface ThreeColumnLayoutProps {
  children: ReactNode;
}

export function ThreeColumnLayout({ children }: ThreeColumnLayoutProps) {
  return (
    <div className="flex h-screen bg-background bg-grid overflow-hidden">
      {/* Left Sidebar - Navigation */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>

      {/* Right Sidebar - Status Panel */}
      <StatusPanel />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add three-column layout component"
```

---

## Task 4: Create New Sidebar Component

**Files:**
- Create: `dashboard/src/components/sidebar-new.tsx`

**Step 1: Create the sidebar**

Create `dashboard/src/components/sidebar-new.tsx`:
```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Brain,
  BarChart3,
  GitCompare,
  TrendingUp,
  Settings,
  HelpCircle,
} from "lucide-react";

const navItems = [
  {
    label: "Overview",
    items: [
      { name: "Dashboard", href: "/", icon: LayoutDashboard },
      { name: "Copy Trading", href: "/wallets", icon: Users },
      { name: "Algo", href: "/algo", icon: Brain },
      { name: "Analyze", href: "/analyze", icon: BarChart3 },
      { name: "Arbitrage", href: "/arbitrage", icon: GitCompare },
    ]
  },
  {
    label: "Activity",
    items: [
      { name: "Markets", href: "/markets", icon: TrendingUp },
    ]
  },
];

const bottomItems = [
  { name: "Help Center", href: "/help", icon: HelpCircle },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 h-screen bg-card/50 border-r border-border flex flex-col">
      {/* Logo & Welcome */}
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-display font-bold tracking-tight bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
          POLYMIND
        </h1>
        <div className="mt-4">
          <p className="text-foreground font-medium">Welcome Back</p>
          <p className="text-xs text-muted-foreground mt-1">
            Last Login: {new Date().toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-6 overflow-auto">
        {navItems.map((section) => (
          <div key={section.label}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 px-3">
              {section.label}
            </p>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
                        isActive
                          ? "bg-violet-500/10 text-violet-400 border-l-2 border-violet-500"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom Items */}
      <div className="p-4 border-t border-border">
        <ul className="space-y-1">
          {bottomItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
                    isActive
                      ? "bg-violet-500/10 text-violet-400"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add new sidebar with navigation sections"
```

---

## Task 5: Create Status Panel (Right Sidebar)

**Files:**
- Create: `dashboard/src/components/status-panel.tsx`

**Step 1: Create the status panel**

Create `dashboard/src/components/status-panel.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  Activity,
  Wallet,
  AlertTriangle,
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
  const [isStarting, setIsStarting] = useState(false);

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
          disabled={isStarting}
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
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add status panel with live crypto prices"
```

---

## Task 6: Create Chart Components

**Files:**
- Create: `dashboard/src/components/charts/pnl-chart.tsx`
- Create: `dashboard/src/components/charts/equity-chart.tsx`
- Create: `dashboard/src/components/charts/index.ts`

**Step 1: Create PnL Bar Chart**

Create `dashboard/src/components/charts/pnl-chart.tsx`:
```tsx
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
                formatter={(value: number) => [`${value.toFixed(2)}%`, "ROI"]}
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
```

**Step 2: Create Equity Area Chart**

Create `dashboard/src/components/charts/equity-chart.tsx`:
```tsx
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
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Equity"]}
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
```

**Step 3: Create index export**

Create `dashboard/src/components/charts/index.ts`:
```ts
export { PnLChart } from "./pnl-chart";
export { EquityChart } from "./equity-chart";
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add PnL and Equity chart components"
```

---

## Task 7: Create New Dashboard Page

**Files:**
- Modify: `dashboard/src/app/page.tsx`

**Step 1: Rewrite the dashboard page**

Replace `dashboard/src/app/page.tsx`:
```tsx
"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { PnLChart, EquityChart } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Home,
  ChevronRight,
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
} from "lucide-react";
import useSWR from "swr";
import { fetcher, Trade, Status } from "@/lib/api";

// Generate sample data for charts
const generatePnLData = () => {
  const data = [];
  const now = new Date();
  for (let i = 14; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
      pnl: Math.random() * 10 - 3, // -3% to +7%
    });
  }
  return data;
};

const generateEquityData = () => {
  const data = [];
  const now = new Date();
  let equity = 1000;
  for (let i = 14; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    equity += Math.random() * 100 - 30;
    data.push({
      date: date.toLocaleDateString("en-US", { day: "numeric", month: "short" }),
      equity: Math.max(equity, 500),
    });
  }
  return data;
};

export default function DashboardPage() {
  const { data: status } = useSWR<Status>("/status", fetcher, { refreshInterval: 5000 });
  const { data: trades } = useSWR<Trade[]>("/trades?limit=5", fetcher, { refreshInterval: 10000 });

  const pnlData = generatePnLData();
  const equityData = generateEquityData();

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb & Search */}
      <div className="flex items-center justify-between mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Home className="h-4 w-4" />
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Overview</span>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 w-64"
          />
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="account" className="mb-8 animate-fade-in stagger-1">
        <TabsList className="bg-secondary/50 border border-border">
          <TabsTrigger value="account">Account Information</TabsTrigger>
          <TabsTrigger value="instance">Bot Performance</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Charts Grid */}
      <div className="space-y-6">
        <div className="animate-fade-in stagger-2">
          <PnLChart data={pnlData} />
        </div>

        <div className="animate-fade-in stagger-3">
          <EquityChart data={equityData} />
        </div>

        {/* Recent Trades */}
        <Card className="glass border-border animate-fade-in stagger-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-display">Recent Trades</CardTitle>
              <Activity className="h-4 w-4 text-emerald-500 animate-pulse-live" />
            </div>
          </CardHeader>
          <CardContent>
            {trades && trades.length > 0 ? (
              <div className="space-y-3">
                {trades.slice(0, 5).map((trade, i) => (
                  <div
                    key={trade.id || i}
                    className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                        trade.side === "YES" ? "bg-emerald-500/10" : "bg-red-500/10"
                      }`}>
                        {trade.side === "YES" ? (
                          <TrendingUp className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {trade.market_title || trade.market_id.slice(0, 20) + "..."}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {trade.wallet_alias || trade.wallet.slice(0, 10) + "..."}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-mono">${trade.size.toFixed(2)}</p>
                      <Badge variant="outline" className={`text-xs ${
                        trade.side === "YES"
                          ? "border-emerald-500/30 text-emerald-400"
                          : "border-red-500/30 text-red-400"
                      }`}>
                        {trade.side}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-8">
                No recent trades
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </ThreeColumnLayout>
  );
}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): redesign main dashboard page with charts and new layout"
```

---

## Task 8: Create Markets Page (Live Crypto)

**Files:**
- Create: `dashboard/src/app/markets/page.tsx`

**Step 1: Create the markets page**

Create `dashboard/src/app/markets/page.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Home,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Activity,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CryptoData {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  price_change_percentage_24h: number;
  market_cap: number;
  total_volume: number;
  sparkline_in_7d?: { price: number[] };
}

export default function MarketsPage() {
  const [cryptos, setCryptos] = useState<CryptoData[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchCryptos = async () => {
    try {
      const res = await fetch(
        "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=true"
      );
      const data = await res.json();
      setCryptos(data);
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Failed to fetch crypto data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCryptos();
    const interval = setInterval(fetchCryptos, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center justify-between mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Home className="h-4 w-4" />
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground">Markets</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Activity className="h-3 w-3 text-emerald-500 animate-pulse-live" />
          {lastUpdate && (
            <span>Updated {lastUpdate.toLocaleTimeString()}</span>
          )}
        </div>
      </div>

      {/* Title */}
      <div className="mb-8 animate-fade-in stagger-1">
        <h1 className="text-2xl font-display font-bold">Crypto Markets</h1>
        <p className="text-muted-foreground mt-1">
          Real-time prices from CoinGecko
        </p>
      </div>

      {/* Crypto Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 animate-fade-in stagger-2">
        {cryptos.map((crypto, i) => (
          <Card
            key={crypto.id}
            className="glass border-border hover:border-violet-500/30 transition-colors"
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-display font-semibold">
                    {crypto.symbol.toUpperCase()}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {crypto.name}
                  </span>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    crypto.price_change_percentage_24h >= 0
                      ? "border-emerald-500/30 text-emerald-400"
                      : "border-red-500/30 text-red-400"
                  )}
                >
                  {crypto.price_change_percentage_24h >= 0 ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  )}
                  {crypto.price_change_percentage_24h.toFixed(2)}%
                </Badge>
              </div>

              <p className="text-2xl font-mono font-bold">
                ${crypto.current_price.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: crypto.current_price < 1 ? 6 : 2
                })}
              </p>

              <div className="mt-3 pt-3 border-t border-border/50 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-muted-foreground">Market Cap</p>
                  <p className="font-mono">
                    ${(crypto.market_cap / 1e9).toFixed(2)}B
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">24h Volume</p>
                  <p className="font-mono">
                    ${(crypto.total_volume / 1e9).toFixed(2)}B
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}
    </ThreeColumnLayout>
  );
}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add markets page with live crypto prices"
```

---

## Task 9: Update Existing Pages to Use New Layout

**Files:**
- Modify: `dashboard/src/app/wallets/page.tsx`
- Modify: `dashboard/src/app/arbitrage/page.tsx`
- Modify: `dashboard/src/app/settings/page.tsx`

**Step 1: Update wallets page**

In `dashboard/src/app/wallets/page.tsx`, replace `DashboardLayout` with `ThreeColumnLayout`:
```tsx
// Change import
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";

// Change wrapper component
<ThreeColumnLayout>
  {/* existing content */}
</ThreeColumnLayout>
```

**Step 2: Update arbitrage page**

In `dashboard/src/app/arbitrage/page.tsx`, same changes.

**Step 3: Update settings page**

In `dashboard/src/app/settings/page.tsx`, same changes.

**Step 4: Commit**

```bash
git add -A && git commit -m "feat(dashboard): migrate existing pages to new layout"
```

---

## Task 10: Create Algo Page (AI Decisions)

**Files:**
- Create: `dashboard/src/app/algo/page.tsx`

**Step 1: Create the algo page**

Create `dashboard/src/app/algo/page.tsx`:
```tsx
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
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add Algo page for AI decision history"
```

---

## Task 11: Create Analyze Page (Performance)

**Files:**
- Create: `dashboard/src/app/analyze/page.tsx`

**Step 1: Create the analyze page**

Create `dashboard/src/app/analyze/page.tsx`:
```tsx
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
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat(dashboard): add Analyze page for performance metrics"
```

---

## Task 12: Final Testing & Cleanup

**Step 1: Run the dashboard**

```bash
cd dashboard && npm run dev
```

**Step 2: Test all pages**

- Visit http://localhost:3000 (Dashboard)
- Visit http://localhost:3000/wallets (Copy Trading)
- Visit http://localhost:3000/algo (AI Decisions)
- Visit http://localhost:3000/analyze (Performance)
- Visit http://localhost:3000/arbitrage (Arbitrage)
- Visit http://localhost:3000/markets (Crypto Prices)
- Visit http://localhost:3000/settings (Settings)

**Step 3: Final commit**

```bash
git add -A && git commit -m "feat(dashboard): complete redesign with midnight terminal theme"
```

---

**Plan complete and saved to `docs/plans/2026-01-09-dashboard-redesign.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
