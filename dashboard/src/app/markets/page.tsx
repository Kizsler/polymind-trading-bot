"use client";

import { useEffect, useState } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent } from "@/components/ui/card";
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
