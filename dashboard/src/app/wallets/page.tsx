"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
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
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/supabase/auth-context";

// Get singleton client outside component
const supabase = createClient();

interface WalletData {
  id: number;
  address: string;
  alias: string | null;
  enabled: boolean;
  win_rate?: number | null;
  total_pnl?: number | null;
}

export default function WalletsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [wallets, setWallets] = useState<WalletData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newWalletAddress, setNewWalletAddress] = useState("");
  const [newWalletAlias, setNewWalletAlias] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Fetch wallets from Supabase
  const fetchWallets = async () => {
    console.log("fetchWallets called", { userId: user?.id });
    if (!user) return;

    try {
      // Get user's custom wallets
      console.log("Fetching user_wallets...");
      const { data: userWallets, error: userError } = await supabase
        .from("user_wallets")
        .select("*")
        .eq("user_id", user.id);

      console.log("user_wallets result:", { userWallets, userError });
      if (userError) throw userError;

      // Get user's selected recommended wallets
      console.log("Fetching user_recommended_selections...");
      const { data: selections, error: selError } = await supabase
        .from("user_recommended_selections")
        .select("id, enabled, wallet_id")
        .eq("user_id", user.id);

      console.log("selections result:", { selections, selError });
      if (selError) throw selError;

      // Get all recommended wallets
      const { data: recommendedWallets } = await supabase
        .from("recommended_wallets")
        .select("*");

      // Create a map of recommended wallets by id
      const recWalletMap: Record<number, WalletData> = {};
      if (recommendedWallets) {
        recommendedWallets.forEach((w: WalletData) => {
          recWalletMap[w.id] = w;
        });
      }

      // Combine wallets
      const allWallets: WalletData[] = [];

      // Add custom wallets
      if (userWallets) {
        userWallets.forEach((w: WalletData) => {
          allWallets.push({
            id: w.id,
            address: w.address,
            alias: w.alias,
            enabled: w.enabled,
          });
        });
      }

      // Add recommended wallets from user selections
      if (selections) {
        selections.forEach((sel: { wallet_id: number; enabled: boolean }) => {
          const recWallet = recWalletMap[sel.wallet_id];
          if (recWallet) {
            allWallets.push({
              id: recWallet.id + 10000, // Offset to avoid ID collision
              address: recWallet.address,
              alias: recWallet.alias,
              enabled: sel.enabled,
              win_rate: recWallet.win_rate,
            });
          }
        });
      }

      // Calculate P&L for each wallet from trades
      const { data: trades } = await supabase
        .from("trades")
        .select("wallet, pnl")
        .eq("user_id", user.id);

      if (trades) {
        const pnlByWallet: Record<string, number> = {};
        trades.forEach((t: { wallet: string; pnl: number | null }) => {
          if (!pnlByWallet[t.wallet]) pnlByWallet[t.wallet] = 0;
          pnlByWallet[t.wallet] += t.pnl || 0;
        });

        allWallets.forEach((w: WalletData) => {
          w.total_pnl = pnlByWallet[w.address] || 0;
        });
      }

      setWallets(allWallets);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch wallets:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log("Wallets useEffect", { authLoading, userId: user?.id });

    // Don't fetch until auth is done loading
    if (authLoading) {
      console.log("Auth still loading, waiting...");
      return;
    }

    if (user) {
      console.log("User found, fetching wallets...");
      fetchWallets();
    } else {
      console.log("No user, setting loading false");
      setLoading(false);
    }
  }, [user, authLoading]);

  const handleAddWallet = async () => {
    if (!newWalletAddress || !user) return;

    setIsAdding(true);
    try {
      const { error } = await supabase.from("user_wallets").insert({
        user_id: user.id,
        address: newWalletAddress.trim(),
        alias: newWalletAlias.trim() || null,
        enabled: true,
      });

      if (error) throw error;

      setNewWalletAddress("");
      setNewWalletAlias("");
      setDialogOpen(false);
      fetchWallets();
    } catch (err: any) {
      console.error("Failed to add wallet:", err);
      alert("Failed to add wallet: " + err.message);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveWallet = async (wallet: WalletData) => {
    if (!user) return;

    try {
      // Check if it's a custom wallet (id < 10000) or recommended (id >= 10000)
      if (wallet.id < 10000) {
        const { error } = await supabase
          .from("user_wallets")
          .delete()
          .eq("id", wallet.id)
          .eq("user_id", user.id);
        if (error) throw error;
      } else {
        // For recommended wallets, just disable the selection
        const { error } = await supabase
          .from("user_recommended_selections")
          .delete()
          .eq("wallet_id", wallet.id - 10000)
          .eq("user_id", user.id);
        if (error) throw error;
      }
      fetchWallets();
    } catch (err: any) {
      console.error("Failed to remove wallet:", err);
      alert("Failed to remove wallet: " + (err.message || "Unknown error"));
    }
  };

  const handleToggleWallet = async (wallet: WalletData) => {
    console.log("Toggle wallet called", { wallet, user: user?.id });
    if (!user) {
      alert("Not logged in - please refresh the page");
      return;
    }

    try {
      if (wallet.id < 10000) {
        console.log("Toggling custom wallet", wallet.id);
        const { error, data } = await supabase
          .from("user_wallets")
          .update({ enabled: !wallet.enabled })
          .eq("id", wallet.id)
          .eq("user_id", user.id)
          .select();
        console.log("Custom wallet toggle result:", { error, data });
        if (error) throw error;
      } else {
        const walletId = wallet.id - 10000;
        console.log("Toggling recommended wallet", { displayId: wallet.id, walletId, userId: user.id });
        const { error, data } = await supabase
          .from("user_recommended_selections")
          .update({ enabled: !wallet.enabled })
          .eq("wallet_id", walletId)
          .eq("user_id", user.id)
          .select();
        console.log("Recommended wallet toggle result:", { error, data });
        if (error) throw error;
      }
      fetchWallets();
    } catch (err: any) {
      console.error("Failed to toggle wallet:", err);
      alert("Failed to toggle wallet: " + (err.message || JSON.stringify(err)));
    }
  };

  const totalPnl = wallets.reduce((acc, w) => acc + (w.total_pnl || 0), 0);
  const avgWinRate = wallets.length
    ? wallets.reduce((acc, w) => acc + (w.win_rate || 0), 0) / wallets.filter(w => w.win_rate).length || 0
    : 0;

  return (
    <ThreeColumnLayout>
      <div>
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
                  <p className="font-medium text-loss">Error Loading Wallets</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {(loading || authLoading) && (
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
        {!loading && !authLoading && (
          <div className="grid gap-4 md:grid-cols-3 mb-8">
            <Card className="bg-card border-border">
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{wallets.length}</div>
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
        )}

        {/* Empty State */}
        {!loading && !authLoading && wallets.length === 0 && (
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
          {wallets.map((wallet) => (
            <Card
              key={wallet.id}
              className="bg-card border-border hover:border-primary/50 transition-colors"
            >
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
                        onClick={(e) => {
                          e.stopPropagation();
                          navigator.clipboard.writeText(wallet.address);
                        }}
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                      <a
                        href={`https://polymarket.com/profile/${wallet.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={wallet.enabled}
                      onCheckedChange={() => handleToggleWallet(wallet)}
                    />
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
                    {wallet.win_rate && (
                      <div>
                        <p className="text-xs text-muted-foreground">Win Rate</p>
                        <p className="text-lg font-bold flex items-center gap-1">
                          {wallet.win_rate.toFixed(0)}%
                          {wallet.win_rate > 50 ? (
                            <TrendingUp className="h-4 w-4 text-profit" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-loss" />
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Type</p>
                      <p className="text-lg font-bold">
                        {wallet.id >= 10000 ? "Recommended" : "Custom"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Status</p>
                      <p className="text-lg font-bold">
                        {wallet.enabled ? "Tracking" : "Paused"}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-border flex items-center justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveWallet(wallet);
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Remove
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </ThreeColumnLayout>
  );
}
