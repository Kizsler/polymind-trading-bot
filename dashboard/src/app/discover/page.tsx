"use client";

import { useState, useEffect } from "react";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Search,
  Loader2,
  TrendingUp,
  ExternalLink,
  Copy,
  Plus,
  Check,
  Users,
  Activity,
  DollarSign,
  UserPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

const supabase = createClient();

// Dev mode check
const DEV_MODE = typeof window !== 'undefined' &&
  process.env.NODE_ENV === "development" &&
  process.env.NEXT_PUBLIC_DEV_MODE === "true";

interface WalletResult {
  address: string;
  trade_count: number;
  total_volume: number;
  buy_volume: number;
  sell_volume: number;
  markets_traded: number;
  avg_buy_price: number;
  avg_sell_price: number;
  estimated_pnl: number;
  is_profitable: boolean;
}

interface ScrapeResult {
  success: boolean;
  criteria: {
    min_trades: number;
    min_volume: number;
    lookback_hours: number;
  };
  total_trades_analyzed: number;
  unique_wallets: number;
  qualifying_wallets: number;
  wallets: WalletResult[];
}

export default function DiscoverPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScrapeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);
  const [trackedWallets, setTrackedWallets] = useState<Set<string>>(new Set());
  const [addingWallet, setAddingWallet] = useState<string | null>(null);

  // Filter settings
  const [minTrades, setMinTrades] = useState(1);
  const [minVolume, setMinVolume] = useState(0);
  const [lookbackHours, setLookbackHours] = useState(48);
  const [profitableOnly, setProfitableOnly] = useState(true);

  // Fetch user's existing tracked wallets
  const fetchTrackedWallets = async () => {
    if (!user) return;

    try {
      // In dev mode, use localStorage
      if (DEV_MODE) {
        const stored = localStorage.getItem("dev_tracked_wallets");
        if (stored) {
          setTrackedWallets(new Set(JSON.parse(stored)));
        }
        return;
      }

      const { data } = await supabase
        .from("user_wallets")
        .select("address")
        .eq("user_id", user.id);

      if (data) {
        setTrackedWallets(new Set(data.map((w: { address: string }) => w.address.toLowerCase())));
      }
    } catch (err) {
      console.error("Failed to fetch tracked wallets:", err);
    }
  };

  useEffect(() => {
    fetchTrackedWallets();
  }, [user]);

  const addToTracking = async (address: string) => {
    if (!user) return;

    setAddingWallet(address);
    try {
      // In dev mode, use localStorage
      if (DEV_MODE) {
        const newSet = new Set([...trackedWallets, address.toLowerCase()]);
        localStorage.setItem("dev_tracked_wallets", JSON.stringify([...newSet]));
        setTrackedWallets(newSet);
        setAddingWallet(null);
        return;
      }

      const { error } = await supabase.from("user_wallets").insert({
        user_id: user.id,
        address: address,
        alias: null,
        enabled: true,
      });

      if (error) throw error;

      // Update tracked wallets set
      setTrackedWallets(prev => new Set([...prev, address.toLowerCase()]));
    } catch (err: any) {
      console.error("Failed to add wallet:", err);
      alert("Failed to add wallet: " + err.message);
    } finally {
      setAddingWallet(null);
    }
  };

  const runScraper = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        min_trades: minTrades.toString(),
        min_volume: minVolume.toString(),
        lookback_hours: lookbackHours.toString(),
        profitable_only: profitableOnly.toString(),
      });
      const response = await fetch(`/api/discover-wallets?${params}`);
      const data = await response.json();

      if (data.success) {
        setResult(data);
      } else {
        setError(data.error || "Failed to scrape wallets");
      }
    } catch (err) {
      setError("Network error - please try again");
    } finally {
      setLoading(false);
    }
  };

  const copyAddress = (address: string) => {
    navigator.clipboard.writeText(address);
    setCopiedAddress(address);
    setTimeout(() => setCopiedAddress(null), 2000);
  };

  return (
    <ThreeColumnLayout>
      <div>
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Discover Wallets</h1>
          <p className="text-muted-foreground mt-1">
            Find active, high-volume traders on Polymarket
          </p>
        </div>

        {/* Scraper Controls */}
        <Card className="mb-8 bg-card border-border">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Wallet Discovery</CardTitle>
            <p className="text-sm text-muted-foreground">
              Find active traders on Polymarket matching your criteria
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Profitable Only Toggle */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div>
                <Label htmlFor="profitableOnly" className="text-sm font-medium text-emerald-400">
                  Profitable Wallets Only
                </Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Only show wallets with positive estimated PnL (selling higher than buying)
                </p>
              </div>
              <Switch
                id="profitableOnly"
                checked={profitableOnly}
                onCheckedChange={setProfitableOnly}
              />
            </div>

            {/* Filter Controls */}
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="minTrades" className="text-sm text-muted-foreground">
                  Min Trades
                </Label>
                <Input
                  id="minTrades"
                  type="number"
                  min={1}
                  value={minTrades}
                  onChange={(e) => setMinTrades(parseInt(e.target.value) || 1)}
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">Minimum number of trades</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="minVolume" className="text-sm text-muted-foreground">
                  Min Volume ($)
                </Label>
                <Input
                  id="minVolume"
                  type="number"
                  min={0}
                  step={100}
                  value={minVolume}
                  onChange={(e) => setMinVolume(parseInt(e.target.value) || 0)}
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">Minimum trading volume in USD</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="lookback" className="text-sm text-muted-foreground">
                  Lookback (hours)
                </Label>
                <Input
                  id="lookback"
                  type="number"
                  min={1}
                  max={168}
                  value={lookbackHours}
                  onChange={(e) => setLookbackHours(parseInt(e.target.value) || 24)}
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">How far back to scan (max 7 days)</p>
              </div>
            </div>

            {/* Scan Button */}
            <div className="flex justify-end">
              <Button
                onClick={runScraper}
                disabled={loading}
                className="gap-2 gradient-violet text-white"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Scan for Wallets
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-red-500/10 border-red-500/30">
            <CardContent className="pt-6">
              <p className="text-red-400">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <>
            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4 mb-8">
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <Activity className="h-5 w-5 text-violet-400" />
                    <div>
                      <div className="text-2xl font-bold">
                        {result.total_trades_analyzed.toLocaleString()}
                      </div>
                      <p className="text-xs text-muted-foreground">Trades Analyzed</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <Users className="h-5 w-5 text-blue-400" />
                    <div>
                      <div className="text-2xl font-bold">
                        {result.unique_wallets.toLocaleString()}
                      </div>
                      <p className="text-xs text-muted-foreground">Unique Wallets</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="h-5 w-5 text-emerald-400" />
                    <div>
                      <div className="text-2xl font-bold">
                        {result.qualifying_wallets}
                      </div>
                      <p className="text-xs text-muted-foreground">Qualifying Wallets</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <DollarSign className="h-5 w-5 text-amber-400" />
                    <div>
                      <div className="text-2xl font-bold">
                        ${result.criteria.min_volume}+
                      </div>
                      <p className="text-xs text-muted-foreground">Min Volume</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Wallet List */}
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                  Top Active Wallets
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.wallets.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">
                    No qualifying wallets found. Try again later.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {result.wallets.map((wallet, index) => (
                      <div
                        key={wallet.address}
                        className="flex items-center justify-between p-4 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-violet-500/20 text-violet-400 font-bold text-sm">
                            {index + 1}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <code className="text-sm font-mono">
                                {wallet.address.slice(0, 10)}...{wallet.address.slice(-8)}
                              </code>
                              <button
                                onClick={() => copyAddress(wallet.address)}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                              >
                                {copiedAddress === wallet.address ? (
                                  <Check className="h-3 w-3 text-emerald-400" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </button>
                              <a
                                href={`https://polymarket.com/profile/${wallet.address}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-foreground transition-colors"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            </div>
                            <div className="flex items-center gap-3 mt-1">
                              <Badge variant="outline" className="text-xs">
                                {wallet.trade_count} trades
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {wallet.markets_traded} markets
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className={`text-lg font-bold ${wallet.estimated_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {wallet.estimated_pnl >= 0 ? '+' : ''}${wallet.estimated_pnl.toLocaleString()}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Est. PnL • Vol: ${wallet.total_volume.toLocaleString()}
                            </div>
                          </div>
                          {trackedWallets.has(wallet.address.toLowerCase()) ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1 text-emerald-400 border-emerald-400/30 cursor-default"
                              disabled
                            >
                              <Check className="h-4 w-4" />
                              Tracking
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              className="gap-1 gradient-violet text-white"
                              onClick={() => addToTracking(wallet.address)}
                              disabled={addingWallet === wallet.address}
                            >
                              {addingWallet === wallet.address ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <UserPlus className="h-4 w-4" />
                              )}
                              Add
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {/* Empty State */}
        {!result && !loading && !error && (
          <Card className="bg-card border-border">
            <CardContent className="py-12 text-center">
              <Search className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No Results Yet</h3>
              <p className="text-muted-foreground mb-4">
                Click &quot;Scan for Wallets&quot; to find active traders on Polymarket
              </p>
              <Button onClick={runScraper} className="gap-2">
                <Search className="h-4 w-4" />
                Start Scanning
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </ThreeColumnLayout>
  );
}
