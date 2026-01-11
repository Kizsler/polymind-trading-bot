"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Loader2,
  ArrowRight,
  ArrowLeft,
  Wallet,
  DollarSign,
  Sparkles,
  Rocket,
  Plus,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RecommendedWallet {
  id: number;
  address: string;
  alias: string;
  description: string;
  win_rate: number;
}

const BALANCE_OPTIONS = [100, 500, 1000, 5000, 10000];

export default function OnboardingPage() {
  const router = useRouter();
  const supabase = createClient();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  // Step 2: Balance
  const [selectedBalance, setSelectedBalance] = useState(1000);

  // Step 3: Wallets
  const [recommendedWallets, setRecommendedWallets] = useState<RecommendedWallet[]>([]);
  const [selectedWallets, setSelectedWallets] = useState<number[]>([]);
  const [customWallets, setCustomWallets] = useState<{ address: string; alias: string }[]>([]);
  const [newWalletAddress, setNewWalletAddress] = useState("");
  const [newWalletAlias, setNewWalletAlias] = useState("");

  // Fetch user and recommended wallets on mount
  useEffect(() => {
    const init = async () => {
      const { data: { user }, error: authError } = await supabase.auth.getUser();
      console.log("Auth check:", { user: user?.id, authError });

      if (authError) {
        console.error("Auth error:", authError);
        return;
      }

      if (user) {
        setUserId(user.id);
        console.log("Set userId:", user.id);

        // Check if already onboarded
        const { data: profile, error: profileError } = await supabase
          .from("profiles")
          .select("onboarding_completed")
          .eq("id", user.id)
          .single();

        console.log("Profile check:", { profile, profileError });

        if (profile?.onboarding_completed) {
          router.push("/");
          return;
        }
      } else {
        console.log("No user found - redirecting to login");
        router.push("/login");
        return;
      }

      // Fetch recommended wallets
      const { data: wallets } = await supabase
        .from("recommended_wallets")
        .select("*")
        .eq("active", true);

      if (wallets && wallets.length > 0) {
        setRecommendedWallets(wallets);
        setSelectedWallets(wallets.map((w) => w.id)); // Select all by default
      }
    };

    init();
  }, [supabase, router]);

  const handleAddCustomWallet = () => {
    if (newWalletAddress.trim()) {
      setCustomWallets([
        ...customWallets,
        {
          address: newWalletAddress.trim(),
          alias: newWalletAlias.trim() || `Custom Wallet ${customWallets.length + 1}`,
        },
      ]);
      setNewWalletAddress("");
      setNewWalletAlias("");
    }
  };

  const handleRemoveCustomWallet = (index: number) => {
    setCustomWallets(customWallets.filter((_, i) => i !== index));
  };

  const handleComplete = async () => {
    if (!userId) {
      console.error("No userId - cannot complete onboarding");
      return;
    }
    setLoading(true);

    try {
      // Update profile with starting balance
      const { error: profileError } = await supabase
        .from("profiles")
        .update({
          starting_balance: selectedBalance,
          copy_percentage: 0.1,
          bot_status: "running",
          onboarding_completed: true,
          updated_at: new Date().toISOString(),
        })
        .eq("id", userId);

      if (profileError) {
        console.error("Profile update error:", profileError);
        throw profileError;
      }

      // Save selected recommended wallets
      if (selectedWallets.length > 0) {
        const selections = selectedWallets.map((walletId) => ({
          user_id: userId,
          wallet_id: walletId,
          enabled: true,
        }));
        const { error: selectionsError } = await supabase.from("user_recommended_selections").insert(selections);
        if (selectionsError) console.error("Selections error:", selectionsError);
      }

      // Save custom wallets
      if (customWallets.length > 0) {
        const customs = customWallets.map((w) => ({
          user_id: userId,
          address: w.address,
          alias: w.alias,
          enabled: true,
        }));
        const { error: customError } = await supabase.from("user_wallets").insert(customs);
        if (customError) console.error("Custom wallets error:", customError);
      }

      // Redirect to dashboard
      router.push("/");
    } catch (error) {
      console.error("Onboarding error:", error);
      alert("Error completing onboarding. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  const toggleWallet = (walletId: number) => {
    setSelectedWallets((prev) =>
      prev.includes(walletId)
        ? prev.filter((id) => id !== walletId)
        : [...prev, walletId]
    );
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={cn(
                "h-2 rounded-full transition-all duration-300",
                s === step ? "w-8 bg-violet-500" : s < step ? "w-8 bg-emerald-500" : "w-8 bg-muted"
              )}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="glass rounded-2xl p-8 border border-border">
          {/* Step 1: Welcome */}
          {step === 1 && (
            <div className="text-center space-y-6">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-emerald-500 mb-4">
                <Sparkles className="h-10 w-10 text-white" />
              </div>
              <h1 className="text-3xl font-display font-bold">Welcome to PolyMind</h1>
              <p className="text-muted-foreground text-lg max-w-md mx-auto">
                Let's set up your paper trading account. You'll be able to test strategies
                risk-free before going live.
              </p>
              <Button
                size="lg"
                className="gradient-violet text-white px-8"
                onClick={() => setStep(2)}
              >
                Get Started <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </div>
          )}

          {/* Step 2: Starting Balance */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-emerald-500/10 mb-4">
                  <DollarSign className="h-8 w-8 text-emerald-500" />
                </div>
                <h2 className="text-2xl font-display font-bold">Starting Balance</h2>
                <p className="text-muted-foreground mt-2">
                  How much would you paper trade with?
                </p>
              </div>

              <div className="grid grid-cols-5 gap-3">
                {BALANCE_OPTIONS.map((amount) => (
                  <button
                    key={amount}
                    onClick={() => setSelectedBalance(amount)}
                    className={cn(
                      "p-4 rounded-xl border-2 transition-all font-mono font-semibold",
                      selectedBalance === amount
                        ? "border-violet-500 bg-violet-500/10 text-violet-400"
                        : "border-border hover:border-violet-500/50"
                    )}
                  >
                    ${amount.toLocaleString()}
                  </button>
                ))}
              </div>

              <p className="text-center text-sm text-muted-foreground">
                This simulates your trading capital. Pick what you'd actually invest.
              </p>

              <div className="flex justify-between pt-4">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back
                </Button>
                <Button className="gradient-violet text-white" onClick={() => setStep(3)}>
                  Continue <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Wallet Selection */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-violet-500/10 mb-4">
                  <Wallet className="h-8 w-8 text-violet-500" />
                </div>
                <h2 className="text-2xl font-display font-bold">Select Wallets</h2>
                <p className="text-muted-foreground mt-2">
                  Choose which wallets to copy trade from
                </p>
              </div>

              {/* Recommended Wallets */}
              {recommendedWallets.length > 0 && (
                <div className="space-y-3">
                  <Label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    PolyMind Recommended
                  </Label>
                  <div className="space-y-2">
                    {recommendedWallets.map((wallet) => (
                      <div
                        key={wallet.id}
                        onClick={() => toggleWallet(wallet.id)}
                        className={cn(
                          "flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all",
                          selectedWallets.includes(wallet.id)
                            ? "border-violet-500 bg-violet-500/5"
                            : "border-border hover:border-violet-500/50"
                        )}
                      >
                        <Checkbox
                          checked={selectedWallets.includes(wallet.id)}
                          className="h-5 w-5"
                        />
                        <div className="flex-1">
                          <p className="font-medium">{wallet.alias}</p>
                          <p className="text-sm text-muted-foreground">{wallet.description}</p>
                        </div>
                        {wallet.win_rate && (
                          <span className="text-emerald-400 font-mono text-sm">
                            {wallet.win_rate}% win rate
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {recommendedWallets.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <p>2 preset wallets are already added, but if you want to add more, add them below!</p>
                </div>
              )}

              {/* Custom Wallets */}
              <div className="space-y-3">
                <Label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Add Custom Wallet
                </Label>

                {customWallets.map((wallet, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30"
                  >
                    <div className="flex-1">
                      <p className="font-medium">{wallet.alias}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {wallet.address.slice(0, 10)}...{wallet.address.slice(-8)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveCustomWallet(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}

                <div className="flex gap-2">
                  <Input
                    placeholder="Wallet address (0x...)"
                    value={newWalletAddress}
                    onChange={(e) => setNewWalletAddress(e.target.value)}
                    className="flex-1"
                  />
                  <Input
                    placeholder="Alias (optional)"
                    value={newWalletAlias}
                    onChange={(e) => setNewWalletAlias(e.target.value)}
                    className="w-40"
                  />
                  <Button variant="outline" onClick={handleAddCustomWallet}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="ghost" onClick={() => setStep(2)}>
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back
                </Button>
                <div className="flex items-center gap-3">
                  <Button
                    variant="ghost"
                    className="text-muted-foreground"
                    onClick={() => setStep(4)}
                  >
                    Skip for now
                  </Button>
                  <Button
                    className="gradient-violet text-white"
                    onClick={() => setStep(4)}
                    disabled={selectedWallets.length === 0 && customWallets.length === 0}
                  >
                    Continue <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Ready */}
          {step === 4 && (
            <div className="text-center space-y-6">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-500 to-violet-500 mb-4">
                <Rocket className="h-10 w-10 text-white" />
              </div>
              <h1 className="text-3xl font-display font-bold">You're All Set!</h1>
              <p className="text-muted-foreground text-lg max-w-md mx-auto">
                Your paper trading bot is ready. Starting balance of{" "}
                <span className="text-emerald-400 font-mono font-semibold">
                  ${selectedBalance.toLocaleString()}
                </span>{" "}
                watching{" "}
                <span className="text-violet-400 font-semibold">
                  {selectedWallets.length + customWallets.length} wallet(s)
                </span>
                .
              </p>

              <div className="flex justify-center gap-4 pt-4">
                <Button variant="ghost" onClick={() => setStep(3)}>
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back
                </Button>
                <Button
                  size="lg"
                  className="gradient-violet text-white px-8"
                  onClick={handleComplete}
                  disabled={loading || !userId}
                >
                  {loading || !userId ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      Launch Dashboard <ArrowRight className="ml-2 h-5 w-5" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
