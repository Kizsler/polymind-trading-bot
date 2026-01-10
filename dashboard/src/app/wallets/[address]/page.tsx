"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  ArrowLeft,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Copy,
  Loader2,
  AlertCircle,
  Save,
  RotateCcw,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import { api, fetcher, WalletDetail } from "@/lib/api";
import Link from "next/link";

export default function WalletDetailPage() {
  const params = useParams();
  const router = useRouter();
  const address = params.address as string;

  const { data: wallet, error, isLoading } = useSWR<WalletDetail>(
    `/wallets/${address}`,
    fetcher,
    { refreshInterval: 30000 }
  );

  // Local state for editable controls
  const [scaleFactor, setScaleFactor] = useState<number>(1.0);
  const [maxTradeSize, setMaxTradeSize] = useState<string>("");
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize local state when wallet loads
  useEffect(() => {
    if (wallet) {
      setScaleFactor(wallet.scale_factor);
      setMaxTradeSize(wallet.max_trade_size?.toString() || "");
      setMinConfidence(wallet.min_confidence);
      setHasChanges(false);
    }
  }, [wallet]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.updateWalletControls(address, {
        scale_factor: scaleFactor,
        max_trade_size: maxTradeSize ? parseFloat(maxTradeSize) : null,
        min_confidence: minConfidence,
      });
      mutate(`/wallets/${address}`);
      setHasChanges(false);
    } catch (err) {
      console.error("Failed to update wallet controls:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (wallet) {
      setScaleFactor(wallet.scale_factor);
      setMaxTradeSize(wallet.max_trade_size?.toString() || "");
      setMinConfidence(wallet.min_confidence);
      setHasChanges(false);
    }
  };

  const updateField = (setter: (v: any) => void, value: any) => {
    setter(value);
    setHasChanges(true);
  };

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Back Button */}
        <Link
          href="/wallets"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Wallets
        </Link>

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">Wallet Not Found</p>
                  <p className="text-sm text-muted-foreground">
                    Unable to load wallet details. The wallet may not exist.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !wallet && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading wallet details...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {wallet && (
          <>
            {/* Header */}
            <div className="mb-8">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    {wallet.alias || "Unnamed Wallet"}
                    <Badge
                      variant="outline"
                      className={
                        wallet.enabled
                          ? "text-profit border-profit/30"
                          : "text-muted-foreground"
                      }
                    >
                      {wallet.enabled ? "Active" : "Paused"}
                    </Badge>
                  </h1>
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-sm text-muted-foreground font-mono">
                      {address}
                    </code>
                    <button
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => navigator.clipboard.writeText(address)}
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <a
                      href={`https://polymarket.com/profile/${address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-4 mb-8">
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className={`text-2xl font-bold ${(wallet.total_pnl || 0) >= 0 ? "text-profit" : "text-loss"}`}>
                    {(wallet.total_pnl || 0) >= 0 ? "+" : ""}${(wallet.total_pnl || 0).toFixed(2)}
                  </div>
                  <p className="text-sm text-muted-foreground">Total P&L</p>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold flex items-center gap-2">
                    {(wallet.win_rate || 0).toFixed(0)}%
                    {(wallet.win_rate || 0) > 50 ? (
                      <TrendingUp className="h-5 w-5 text-profit" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-loss" />
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">Win Rate</p>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    {(wallet.avg_roi || 0).toFixed(1)}%
                  </div>
                  <p className="text-sm text-muted-foreground">Avg ROI</p>
                </CardContent>
              </Card>
              <Card className="bg-card border-border">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">{wallet.total_trades}</div>
                  <p className="text-sm text-muted-foreground">Total Trades</p>
                </CardContent>
              </Card>
            </div>

            {/* Trading Controls */}
            <Card className="bg-card border-border">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Trading Controls</CardTitle>
                  {hasChanges && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleReset}
                        disabled={isSaving}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset
                      </Button>
                      <Button size="sm" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save Changes
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-3">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Scale Factor
                    </label>
                    <p className="text-xs text-muted-foreground/70 mt-0.5 mb-2">
                      Multiply trade sizes by this factor (1.0 = copy exact size)
                    </p>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="10"
                      value={scaleFactor}
                      onChange={(e) => updateField(setScaleFactor, parseFloat(e.target.value) || 1)}
                      className="bg-background"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Max Trade Size ($)
                    </label>
                    <p className="text-xs text-muted-foreground/70 mt-0.5 mb-2">
                      Maximum size per trade (leave empty for no limit)
                    </p>
                    <Input
                      type="number"
                      step="10"
                      min="0"
                      placeholder="No limit"
                      value={maxTradeSize}
                      onChange={(e) => updateField(setMaxTradeSize, e.target.value)}
                      className="bg-background"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Min Confidence
                    </label>
                    <p className="text-xs text-muted-foreground/70 mt-0.5 mb-2">
                      Only copy trades with AI confidence above this (0-1)
                    </p>
                    <Input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={minConfidence}
                      onChange={(e) => updateField(setMinConfidence, parseFloat(e.target.value) || 0)}
                      className="bg-background"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
