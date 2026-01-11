"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/supabase/auth-context";
import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Wallet,
  Plus,
  Trash2,
  LogOut,
  RefreshCw,
  Home,
  ChevronRight,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RecommendedWallet {
  id: number;
  address: string;
  alias: string;
  description: string;
  win_rate: number;
}

interface UserWallet {
  id: number;
  address: string;
  alias: string;
  enabled: boolean;
}

interface UserSelection {
  wallet_id: number;
  enabled: boolean;
}

export default function AccountPage() {
  const supabase = createClient();
  const { user, profile, signOut, refreshProfile } = useAuth();

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Profile settings
  const [displayName, setDisplayName] = useState("");

  // Wallets
  const [recommendedWallets, setRecommendedWallets] = useState<RecommendedWallet[]>([]);
  const [userSelections, setUserSelections] = useState<UserSelection[]>([]);
  const [userWallets, setUserWallets] = useState<UserWallet[]>([]);
  const [newWalletAddress, setNewWalletAddress] = useState("");
  const [newWalletAlias, setNewWalletAlias] = useState("");

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name || "");
    }
  }, [profile]);

  useEffect(() => {
    const fetchWallets = async () => {
      if (!user) return;

      const { data: recommended } = await supabase
        .from("recommended_wallets")
        .select("*")
        .eq("active", true);
      if (recommended) setRecommendedWallets(recommended);

      const { data: selections } = await supabase
        .from("user_recommended_selections")
        .select("wallet_id, enabled")
        .eq("user_id", user.id);
      if (selections) setUserSelections(selections);

      const { data: custom } = await supabase
        .from("user_wallets")
        .select("*")
        .eq("user_id", user.id);
      if (custom) setUserWallets(custom);
    };

    fetchWallets();
  }, [user, supabase]);

  const handleSaveProfile = async () => {
    if (!user) return;
    setLoading(true);
    setMessage(null);

    try {
      await supabase
        .from("profiles")
        .update({
          display_name: displayName || null,
          updated_at: new Date().toISOString(),
        })
        .eq("id", user.id);

      await refreshProfile();
      setMessage({ type: "success", text: "Profile saved!" });
    } catch (error: any) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  };

  const toggleRecommendedWallet = async (walletId: number, currentlyEnabled: boolean) => {
    if (!user) return;

    const existing = userSelections.find((s) => s.wallet_id === walletId);

    if (existing) {
      await supabase
        .from("user_recommended_selections")
        .update({ enabled: !currentlyEnabled })
        .eq("user_id", user.id)
        .eq("wallet_id", walletId);
    } else {
      await supabase.from("user_recommended_selections").insert({
        user_id: user.id,
        wallet_id: walletId,
        enabled: true,
      });
    }

    const { data } = await supabase
      .from("user_recommended_selections")
      .select("wallet_id, enabled")
      .eq("user_id", user.id);
    if (data) setUserSelections(data);
  };

  const isWalletEnabled = (walletId: number) => {
    const selection = userSelections.find((s) => s.wallet_id === walletId);
    return selection?.enabled ?? false;
  };

  const handleAddCustomWallet = async () => {
    if (!user || !newWalletAddress.trim()) return;

    await supabase.from("user_wallets").insert({
      user_id: user.id,
      address: newWalletAddress.trim(),
      alias: newWalletAlias.trim() || null,
      enabled: true,
    });

    const { data } = await supabase
      .from("user_wallets")
      .select("*")
      .eq("user_id", user.id);
    if (data) setUserWallets(data);

    setNewWalletAddress("");
    setNewWalletAlias("");
  };

  const handleToggleCustomWallet = async (walletId: number, enabled: boolean) => {
    if (!user) return;

    await supabase
      .from("user_wallets")
      .update({ enabled: !enabled })
      .eq("id", walletId)
      .eq("user_id", user.id);

    const { data } = await supabase
      .from("user_wallets")
      .select("*")
      .eq("user_id", user.id);
    if (data) setUserWallets(data);
  };

  const handleDeleteCustomWallet = async (walletId: number) => {
    if (!user) return;

    await supabase
      .from("user_wallets")
      .delete()
      .eq("id", walletId)
      .eq("user_id", user.id);

    setUserWallets(userWallets.filter((w) => w.id !== walletId));
  };

  const handleResetAccount = async () => {
    if (!user) return;
    if (!confirm("This will delete all your trades and reset your balance. Continue?")) {
      return;
    }

    setLoading(true);
    try {
      await supabase.from("trades").delete().eq("user_id", user.id);
      await refreshProfile();
      setMessage({ type: "success", text: "Account reset! Starting fresh." });
    } catch (error: any) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThreeColumnLayout>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
        <Home className="h-4 w-4" />
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground">Account</span>
      </div>

      <h1 className="text-3xl font-display font-bold mb-8">Account</h1>

      <div className="space-y-6">
        {/* Profile */}
        <Card className="glass border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5 text-violet-400" />
              Profile
            </CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={user?.email || ""} disabled className="bg-secondary/30" />
            </div>

            <div className="space-y-2">
              <Label>Display Name</Label>
              <Input
                placeholder="Enter your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-muted-foreground">Starting Balance</Label>
                <p className="text-2xl font-mono font-bold text-emerald-400">
                  ${profile?.starting_balance?.toLocaleString() || "1,000"}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Copy %</Label>
                <p className="text-2xl font-mono font-bold">
                  {((profile?.copy_percentage || 0.1) * 100).toFixed(0)}%
                </p>
              </div>
            </div>

            {message && (
              <div
                className={cn(
                  "p-3 rounded-lg text-sm",
                  message.type === "success"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-red-500/10 text-red-400"
                )}
              >
                {message.text}
              </div>
            )}

            <Button onClick={handleSaveProfile} disabled={loading}>
              {loading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Recommended Wallets */}
        <Card className="glass border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-emerald-400" />
              PolyMind Recommended Wallets
            </CardTitle>
            <CardDescription>Toggle which recommended wallets to copy</CardDescription>
          </CardHeader>
          <CardContent>
            {recommendedWallets.length > 0 ? (
              <div className="space-y-3">
                {recommendedWallets.map((wallet) => {
                  const enabled = isWalletEnabled(wallet.id);
                  return (
                    <div
                      key={wallet.id}
                      className={cn(
                        "flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all",
                        enabled
                          ? "border-emerald-500/50 bg-emerald-500/5"
                          : "border-border hover:border-muted-foreground/50"
                      )}
                      onClick={() => toggleRecommendedWallet(wallet.id, enabled)}
                    >
                      <div>
                        <p className="font-medium">{wallet.alias}</p>
                        <p className="text-sm text-muted-foreground">{wallet.description}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        {wallet.win_rate && (
                          <Badge variant="outline" className="text-emerald-400 border-emerald-500/30">
                            {wallet.win_rate}% WR
                          </Badge>
                        )}
                        {enabled ? (
                          <Check className="h-5 w-5 text-emerald-500" />
                        ) : (
                          <div className="h-5 w-5 rounded border border-muted-foreground/30" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-4">
                No recommended wallets available yet.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Custom Wallets */}
        <Card className="glass border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-amber-400" />
              My Custom Wallets
            </CardTitle>
            <CardDescription>Add your own wallet addresses to copy</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {userWallets.length > 0 && (
              <div className="space-y-2">
                {userWallets.map((wallet) => (
                  <div
                    key={wallet.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/30"
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleToggleCustomWallet(wallet.id, wallet.enabled)}
                        className={cn(
                          "h-5 w-5 rounded flex items-center justify-center transition-colors",
                          wallet.enabled
                            ? "bg-emerald-500 text-white"
                            : "border border-muted-foreground/30"
                        )}
                      >
                        {wallet.enabled && <Check className="h-3 w-3" />}
                      </button>
                      <div>
                        <p className="font-medium">{wallet.alias || "Custom Wallet"}</p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {wallet.address.slice(0, 10)}...{wallet.address.slice(-8)}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteCustomWallet(wallet.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <Input
                placeholder="Wallet address (0x...)"
                value={newWalletAddress}
                onChange={(e) => setNewWalletAddress(e.target.value)}
                className="flex-1"
              />
              <Input
                placeholder="Alias"
                value={newWalletAlias}
                onChange={(e) => setNewWalletAlias(e.target.value)}
                className="w-32"
              />
              <Button variant="outline" onClick={handleAddCustomWallet}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-500/30">
          <CardHeader>
            <CardTitle className="text-red-400">Danger Zone</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Reset Paper Account</p>
                <p className="text-sm text-muted-foreground">
                  Delete all trades and start fresh
                </p>
              </div>
              <Button
                variant="outline"
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                onClick={handleResetAccount}
                disabled={loading}
              >
                Reset
              </Button>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Sign Out</p>
                <p className="text-sm text-muted-foreground">
                  Sign out of your account
                </p>
              </div>
              <Button variant="outline" onClick={signOut}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </ThreeColumnLayout>
  );
}
