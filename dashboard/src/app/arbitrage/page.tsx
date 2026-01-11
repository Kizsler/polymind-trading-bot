"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  GitCompare,
  ArrowRight,
  TrendingUp,
  Zap,
  RefreshCw,
  HelpCircle,
  ArrowLeftRight,
  DollarSign,
  Target,
  Construction,
} from "lucide-react";
import { useState, useEffect } from "react";
import useSWR, { mutate } from "swr";
import { api, fetcher, MarketMapping, ArbitrageOpportunity } from "@/lib/api";

// Check if API is configured
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function ArbitragePage() {
  // Show coming soon if API not configured
  if (!API_URL) {
    return (
      <ThreeColumnLayout>
        <div className="flex flex-col items-center justify-center py-20">
          <div className="h-20 w-20 rounded-2xl bg-violet-500/10 flex items-center justify-center mb-6">
            <Construction className="h-10 w-10 text-violet-400" />
          </div>
          <h1 className="text-2xl font-bold mb-2">Arbitrage Coming Soon</h1>
          <p className="text-muted-foreground text-center max-w-md">
            Cross-platform arbitrage between Polymarket and Kalshi will be available in a future update.
            For now, focus on copy trading with the main dashboard.
          </p>
          <Button variant="outline" className="mt-6" onClick={() => window.location.href = "/"}>
            Back to Dashboard
          </Button>
        </div>
      </ThreeColumnLayout>
    );
  }

  const [polymarketId, setPolymarketId] = useState("");
  const [kalshiId, setKalshiId] = useState("");
  const [description, setDescription] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);

  // Check if first time visiting
  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem("arbitrage_welcome_seen");
    if (!hasSeenWelcome) {
      setShowWelcome(true);
    }
  }, []);

  const handleCloseWelcome = () => {
    localStorage.setItem("arbitrage_welcome_seen", "true");
    setShowWelcome(false);
  };

  const { data: mappings, error: mappingsError, isLoading: mappingsLoading } = useSWR<MarketMapping[]>(
    "/arbitrage/mappings",
    fetcher,
    { refreshInterval: 30000 }
  );

  const { data: opportunities, error: oppsError, isLoading: oppsLoading } = useSWR<ArbitrageOpportunity[]>(
    "/arbitrage/opportunities",
    fetcher,
    { refreshInterval: 5000 }
  );

  const handleAddMapping = async () => {
    if (!polymarketId.trim() && !kalshiId.trim()) return;

    setIsAdding(true);
    try {
      await api.addMapping({
        polymarket_id: polymarketId.trim() || null,
        kalshi_id: kalshiId.trim() || null,
        description: description.trim() || null,
        active: true,
      });
      setPolymarketId("");
      setKalshiId("");
      setDescription("");
      setDialogOpen(false);
      mutate("/arbitrage/mappings");
    } catch (err) {
      console.error("Failed to add mapping:", err);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveMapping = async (id: number) => {
    try {
      await api.removeMapping(id);
      mutate("/arbitrage/mappings");
    } catch (err) {
      console.error("Failed to remove mapping:", err);
    }
  };

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const result = await api.scanArbitrage();
      setLastScanTime(result.scanned_at);
      mutate("/arbitrage/opportunities");
    } catch (err) {
      console.error("Failed to scan:", err);
    } finally {
      setIsScanning(false);
    }
  };

  const error = mappingsError || oppsError;
  const isLoading = mappingsLoading || oppsLoading;

  const activeMappings = mappings?.filter((m) => m.active) || [];
  const totalSpread = opportunities?.reduce((acc, o) => acc + o.spread, 0) || 0;

  return (
    <ThreeColumnLayout>
      <div>
        {/* Welcome Dialog for First Time Users */}
        <Dialog open={showWelcome} onOpenChange={setShowWelcome}>
          <DialogContent className="bg-card border-border max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-xl">
                <ArrowLeftRight className="h-5 w-5 text-violet-400" />
                Welcome to Arbitrage
              </DialogTitle>
              <DialogDescription className="text-muted-foreground">
                Profit from price differences across prediction markets
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="flex gap-3">
                <div className="h-10 w-10 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                  <HelpCircle className="h-5 w-5 text-violet-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">What is Arbitrage?</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Arbitrage exploits price differences between markets. When the same event is priced differently on Polymarket vs Kalshi, you can profit by buying low on one and selling high on the other.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                  <DollarSign className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">Example</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    If "BTC hits $100K" is 60% on Polymarket but 65% on Kalshi, buy YES on Polymarket and NO on Kalshi. You profit the 5% spread regardless of outcome.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="h-10 w-10 rounded-lg bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
                  <Target className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">How to Use</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    1. Click "Add Mapping" to link matching markets<br />
                    2. Click "Scan Now" to find opportunities<br />
                    3. Execute trades when spreads appear
                  </p>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleCloseWelcome} className="w-full">
                Got it, let's go!
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Arbitrage</h1>
            <p className="text-muted-foreground mt-1">
              Cross-platform arbitrage between Polymarket and Kalshi
              {lastScanTime && (
                <span className="ml-2 text-xs">
                  (Last scan: {new Date(lastScanTime).toLocaleTimeString()})
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowWelcome(true)}
              title="How it works"
            >
              <HelpCircle className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="gap-2"
              onClick={handleScan}
              disabled={isScanning}
            >
              {isScanning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {isScanning ? "Scanning..." : "Scan Now"}
            </Button>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Add Mapping
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader>
                <DialogTitle>Add Market Mapping</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Polymarket ID
                  </label>
                  <Input
                    placeholder="0x..."
                    value={polymarketId}
                    onChange={(e) => setPolymarketId(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Kalshi ID
                  </label>
                  <Input
                    placeholder="e.g., KXBTC-100K"
                    value={kalshiId}
                    onChange={(e) => setKalshiId(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Description
                  </label>
                  <Input
                    placeholder="e.g., BTC hits 100K in 2025"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <Button
                  className="w-full"
                  onClick={handleAddMapping}
                  disabled={isAdding || (!polymarketId.trim() && !kalshiId.trim())}
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Adding...
                    </>
                  ) : (
                    "Add Mapping"
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">API Connection Error</p>
                  <p className="text-sm text-muted-foreground">
                    Unable to load arbitrage data. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !mappings && !opportunities && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading arbitrage data...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{activeMappings.length}</div>
              <p className="text-sm text-muted-foreground">Active Mappings</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-primary">{opportunities?.length || 0}</div>
              <p className="text-sm text-muted-foreground">Live Opportunities</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-profit">
                {(totalSpread * 100).toFixed(1)}%
              </div>
              <p className="text-sm text-muted-foreground">Total Spread</p>
            </CardContent>
          </Card>
        </div>

        {/* Live Opportunities */}
        <Card className="bg-card border-border mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary pulse-live" />
              Live Opportunities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {opportunities && opportunities.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  No arbitrage opportunities detected right now.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {opportunities?.map((opp, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-4 rounded-lg bg-secondary/50 border border-border"
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <p className="text-xs text-muted-foreground">Polymarket</p>
                        <p className="text-lg font-bold">{(opp.poly_price * 100).toFixed(0)}%</p>
                      </div>
                      <ArrowRight className={`h-4 w-4 ${opp.direction === "BUY_YES" ? "text-profit" : "text-loss"}`} />
                      <div className="text-center">
                        <p className="text-xs text-muted-foreground">Kalshi</p>
                        <p className="text-lg font-bold">{(opp.kalshi_price * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-profit" />
                        <span className="text-xl font-bold text-profit">
                          {(Math.abs(opp.spread) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <Badge
                        variant="outline"
                        className={
                          opp.direction === "BUY_YES"
                            ? "mt-1 text-profit border-profit/30"
                            : "mt-1 text-loss border-loss/30"
                        }
                      >
                        {opp.direction === "BUY_YES" ? "Buy YES" : "Buy NO"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Market Mappings */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              Market Mappings
            </CardTitle>
          </CardHeader>
          <CardContent>
            {mappings && mappings.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  No market mappings configured. Add a mapping to enable cross-platform arbitrage.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Polymarket ID</TableHead>
                    <TableHead>Kalshi ID</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mappings?.map((mapping) => (
                    <TableRow key={mapping.id}>
                      <TableCell className="font-mono text-xs">
                        {mapping.polymarket_id
                          ? `${mapping.polymarket_id.slice(0, 10)}...`
                          : "-"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {mapping.kalshi_id || "-"}
                      </TableCell>
                      <TableCell>{mapping.description || "-"}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            mapping.active
                              ? "text-profit border-profit/30"
                              : "text-muted-foreground"
                          }
                        >
                          {mapping.active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRemoveMapping(mapping.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </ThreeColumnLayout>
  );
}
