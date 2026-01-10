"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Plus,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Trash2,
  Copy,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { api, fetcher } from "@/lib/api";

interface WalletData {
  id: number;
  address: string;
  alias: string | null;
  enabled: boolean;
  win_rate: number | null;
  total_pnl: number | null;
}

export default function WalletsPage() {
  const [newWalletAddress, setNewWalletAddress] = useState("");
  const [newWalletAlias, setNewWalletAlias] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Fetch wallets from API
  const { data: wallets, error, isLoading } = useSWR<WalletData[]>(
    "/wallets",
    fetcher,
    { refreshInterval: 10000 }
  );

  const handleAddWallet = async () => {
    if (!newWalletAddress) return;

    setIsAdding(true);
    try {
      await api.addWallet(newWalletAddress, newWalletAlias || undefined);
      setNewWalletAddress("");
      setNewWalletAlias("");
      setDialogOpen(false);
      mutate("/wallets");
    } catch (err) {
      console.error("Failed to add wallet:", err);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveWallet = async (address: string) => {
    try {
      await api.removeWallet(address);
      mutate("/wallets");
    } catch (err) {
      console.error("Failed to remove wallet:", err);
    }
  };

  const totalPnl = wallets?.reduce((acc, w) => acc + (w.total_pnl || 0), 0) || 0;
  const avgWinRate = wallets?.length
    ? wallets.reduce((acc, w) => acc + (w.win_rate || 0), 0) / wallets.length
    : 0;

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Wallets</h1>
            <p className="text-muted-foreground mt-1">
              Manage the wallets you&apos;re copy trading
            </p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Add Wallet
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader>
                <DialogTitle>Add New Wallet</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Wallet Address
                  </label>
                  <Input
                    placeholder="0x..."
                    value={newWalletAddress}
                    onChange={(e) => setNewWalletAddress(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Alias (optional)
                  </label>
                  <Input
                    placeholder="e.g., Whale Trader"
                    value={newWalletAlias}
                    onChange={(e) => setNewWalletAlias(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <Button
                  className="w-full"
                  onClick={handleAddWallet}
                  disabled={isAdding || !newWalletAddress}
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Adding...
                    </>
                  ) : (
                    "Add Wallet"
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
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
                    Unable to load wallets. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !wallets && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading wallets...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{wallets?.length || 0}</div>
              <p className="text-sm text-muted-foreground">Total Wallets</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className={`text-2xl font-bold ${totalPnl >= 0 ? "text-profit" : "text-loss"}`}>
                {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}
              </div>
              <p className="text-sm text-muted-foreground">Combined P&L</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {avgWinRate.toFixed(0)}%
              </div>
              <p className="text-sm text-muted-foreground">Avg Win Rate</p>
            </CardContent>
          </Card>
        </div>

        {/* Empty State */}
        {wallets && wallets.length === 0 && (
          <Card className="bg-card border-border">
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground mb-4">
                No wallets tracked yet. Add a wallet to start copy trading.
              </p>
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Wallet
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Wallets Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {wallets?.map((wallet) => (
            <Card key={wallet.id} className="bg-card border-border">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
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
                    </CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs text-muted-foreground font-mono">
                        {wallet.address.slice(0, 10)}...{wallet.address.slice(-8)}
                      </code>
                      <button
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => navigator.clipboard.writeText(wallet.address)}
                      >
                        <Copy className="h-3 w-3" />
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
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch checked={wallet.enabled} />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Total P&L</p>
                      <p
                        className={`text-lg font-bold tabular-nums ${
                          (wallet.total_pnl || 0) >= 0 ? "text-profit" : "text-loss"
                        }`}
                      >
                        {(wallet.total_pnl || 0) >= 0 ? "+" : ""}${(wallet.total_pnl || 0).toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Win Rate</p>
                      <p className="text-lg font-bold flex items-center gap-1">
                        {(wallet.win_rate || 0).toFixed(0)}%
                        {(wallet.win_rate || 0) > 50 ? (
                          <TrendingUp className="h-4 w-4 text-profit" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-loss" />
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Wallet ID</p>
                      <p className="text-lg font-bold tabular-nums">#{wallet.id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Status</p>
                      <p className="text-lg font-bold">
                        {wallet.enabled ? "Tracking" : "Paused"}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    ID: {wallet.id}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleRemoveWallet(wallet.address)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
