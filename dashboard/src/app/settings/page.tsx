"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertCircle,
  AlertOctagon,
  Bell,
  Bot,
  CheckCircle,
  DollarSign,
  Key,
  Loader2,
  Lock,
  LogOut,
  Play,
  Save,
  Shield,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/supabase/auth-context";
import { createClient } from "@/lib/supabase/client";

interface TradeSettings {
  copy_percentage: number;
  max_daily_exposure: number;
  max_trades_per_day: number;
  min_account_balance: number;
  ai_enabled: boolean;
  confidence_threshold: number;
  auto_trade: boolean;
}

export default function SettingsPage() {
  const { user, profile, loading: authLoading } = useAuth();
  const supabase = createClient();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await supabase.auth.signOut();
      router.push("/login");
    } catch (err) {
      console.error("Failed to logout:", err);
    } finally {
      setIsLoggingOut(false);
    }
  };

  // Local state for form - initialize from profile when available
  const [formData, setFormData] = useState<TradeSettings>({
    copy_percentage: profile?.copy_percentage ?? 0.1,
    max_daily_exposure: profile?.max_daily_exposure ?? 500,
    max_trades_per_day: profile?.max_trades_per_day ?? 10,
    min_account_balance: profile?.min_account_balance ?? 100,
    ai_enabled: profile?.ai_enabled ?? true,
    confidence_threshold: profile?.confidence_threshold ?? 0.7,
    auto_trade: profile?.auto_trade ?? true,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Notification settings (local only for now)
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [notifyOnTrade, setNotifyOnTrade] = useState(true);
  const [notifyOnSkip, setNotifyOnSkip] = useState(false);
  const [notifyOnError, setNotifyOnError] = useState(true);

  // Emergency stop state
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(profile?.bot_status === "stopped");
  const [isStopLoading, setIsStopLoading] = useState(false);

  // Sync form data when profile loads
  useEffect(() => {
    if (profile) {
      setFormData({
        copy_percentage: profile.copy_percentage ?? 0.1,
        max_daily_exposure: profile.max_daily_exposure ?? 500,
        max_trades_per_day: profile.max_trades_per_day ?? 10,
        min_account_balance: profile.min_account_balance ?? 100,
        ai_enabled: profile.ai_enabled ?? true,
        confidence_threshold: profile.confidence_threshold ?? 0.7,
        auto_trade: profile.auto_trade ?? true,
      });
      setIsEmergencyStopped(profile.bot_status === "stopped");
    }
  }, [profile]);

  const handleEmergencyStop = async () => {
    if (!user) return;
    setIsStopLoading(true);
    try {
      await supabase
        .from("profiles")
        .update({ bot_status: "stopped" })
        .eq("id", user.id);
      setIsEmergencyStopped(true);
    } catch (err) {
      console.error("Failed to activate emergency stop:", err);
    } finally {
      setIsStopLoading(false);
    }
  };

  const handleResumeTrading = async () => {
    if (!user) return;
    setIsStopLoading(true);
    try {
      await supabase
        .from("profiles")
        .update({ bot_status: "running" })
        .eq("id", user.id);
      setIsEmergencyStopped(false);
    } catch (err) {
      console.error("Failed to resume trading:", err);
    } finally {
      setIsStopLoading(false);
    }
  };

  const handleSave = async () => {
    if (!user) return;
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const { error } = await supabase
        .from("profiles")
        .update({
          copy_percentage: formData.copy_percentage,
          max_daily_exposure: formData.max_daily_exposure,
          max_trades_per_day: formData.max_trades_per_day,
          min_account_balance: formData.min_account_balance,
          ai_enabled: formData.ai_enabled,
          confidence_threshold: formData.confidence_threshold,
          auto_trade: formData.auto_trade,
        })
        .eq("id", user.id);

      if (error) throw error;

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const updateField = <K extends keyof TradeSettings>(key: K, value: TradeSettings[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const startingBalance = profile?.starting_balance ?? 1000;

  return (
    <ThreeColumnLayout>
      <div>
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Configure your trading bot parameters and preferences
          </p>
        </div>

        {/* Not logged in state */}
        {!user && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">Not Logged In</p>
                  <p className="text-sm text-muted-foreground">
                    Please log in to access your settings.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {authLoading && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading settings...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {user && !authLoading && (
          <Tabs defaultValue="trading" className="space-y-6">
            <TabsList className="bg-secondary">
              <TabsTrigger value="trading" className="gap-2">
                <DollarSign className="h-4 w-4" />
                Trading
              </TabsTrigger>
              <TabsTrigger value="ai" className="gap-2">
                <Bot className="h-4 w-4" />
                AI Engine
              </TabsTrigger>
              <TabsTrigger value="risk" className="gap-2">
                <Shield className="h-4 w-4" />
                Risk Limits
              </TabsTrigger>
              <TabsTrigger value="notifications" className="gap-2">
                <Bell className="h-4 w-4" />
                Notifications
              </TabsTrigger>
              <TabsTrigger value="api" className="gap-2">
                <Key className="h-4 w-4" />
                API Keys
              </TabsTrigger>
            </TabsList>

            {/* Trading Settings */}
            <TabsContent value="trading">
              <div className="grid gap-6">
                <Card className="bg-card border-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-primary" />
                      Trading Mode
                    </CardTitle>
                    <CardDescription>
                      Paper trading mode - all trades are simulated
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Current Mode</p>
                        <p className="text-sm text-muted-foreground">
                          Paper trading uses simulated funds
                        </p>
                      </div>
                      <Badge variant="outline" className="border-violet-500/30 text-violet-400">
                        Paper Mode
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-border">
                      <div>
                        <p className="font-medium">Auto-Trade</p>
                        <p className="text-sm text-muted-foreground">
                          Automatically execute AI-approved trades
                        </p>
                      </div>
                      <Switch
                        checked={formData.auto_trade}
                        onCheckedChange={(checked) => updateField("auto_trade", checked)}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lock className="h-5 w-5 text-amber-500" />
                      Paper Trading Balance
                    </CardTitle>
                    <CardDescription>
                      Your virtual starting balance for paper trading
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Starting Balance ($)
                      </label>
                      <Input
                        type="number"
                        value={startingBalance}
                        disabled
                        className="mt-1.5 bg-secondary/50 cursor-not-allowed"
                      />
                      <p className="text-xs text-amber-400 mt-2 flex items-center gap-1.5">
                        <Lock className="h-3 w-3" />
                        If wanting a higher or lower amount contact @Kizsler
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader>
                    <CardTitle>Position Sizing</CardTitle>
                    <CardDescription>
                      Control how much capital is used per trade
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Copy Percentage (%)
                        </label>
                        <Input
                          type="number"
                          step="5"
                          min="1"
                          max="200"
                          value={(formData.copy_percentage * 100).toFixed(0)}
                          onChange={(e) => updateField("copy_percentage", parseFloat(e.target.value) / 100)}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          What % of detected trade size to copy
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Max Daily Exposure ($)
                        </label>
                        <Input
                          type="number"
                          value={formData.max_daily_exposure}
                          onChange={(e) => updateField("max_daily_exposure", parseFloat(e.target.value))}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Total open position limit per day
                        </p>
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2 pt-4 border-t border-border">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Max Trades Per Day
                        </label>
                        <Input
                          type="number"
                          min="1"
                          max="100"
                          value={formData.max_trades_per_day}
                          onChange={(e) => updateField("max_trades_per_day", parseInt(e.target.value))}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Maximum number of trades allowed per day
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Min Account Balance ($)
                        </label>
                        <Input
                          type="number"
                          min="0"
                          value={formData.min_account_balance}
                          onChange={(e) => updateField("min_account_balance", parseFloat(e.target.value))}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Stop trading if balance falls below this
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* AI Settings */}
            <TabsContent value="ai">
              <div className="grid gap-6">
                <Card className="bg-card border-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Bot className="h-5 w-5 text-primary" />
                      AI Decision Engine
                    </CardTitle>
                    <CardDescription>
                      AI-powered trade filtering and analysis
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8">
                      <Bot className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                      <p className="text-lg font-medium text-muted-foreground">Coming Soon</p>
                      <p className="text-sm text-muted-foreground mt-2">
                        Contact <span className="text-primary font-medium">@Kizsler</span> for testing
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Risk Limits */}
            <TabsContent value="risk">
              <div className="grid gap-6">
                {/* Emergency Stop Card */}
                <Card className={`border-2 ${isEmergencyStopped ? 'bg-loss/10 border-loss' : 'bg-card border-border'}`}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertOctagon className={`h-5 w-5 ${isEmergencyStopped ? 'text-loss' : 'text-primary'}`} />
                      Emergency Stop
                    </CardTitle>
                    <CardDescription>
                      Instantly halt all trading activity
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">
                          {isEmergencyStopped ? 'Trading is STOPPED' : 'Trading is active'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {isEmergencyStopped
                            ? 'All trading is halted. Click resume to continue.'
                            : 'Click the button to immediately stop all trading.'}
                        </p>
                      </div>
                      {isEmergencyStopped ? (
                        <Button
                          variant="outline"
                          className="gap-2 border-profit text-profit hover:bg-profit/10"
                          onClick={handleResumeTrading}
                          disabled={isStopLoading}
                        >
                          {isStopLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                          Resume Trading
                        </Button>
                      ) : (
                        <Button
                          variant="destructive"
                          className="gap-2"
                          onClick={handleEmergencyStop}
                          disabled={isStopLoading}
                        >
                          {isStopLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <AlertOctagon className="h-4 w-4" />
                          )}
                          Emergency Stop
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader>
                    <CardTitle>Account Protection</CardTitle>
                    <CardDescription>
                      Automatic safeguards to protect your capital
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Minimum Account Balance ($)
                        </label>
                        <Input
                          type="number"
                          value={formData.min_account_balance}
                          onChange={(e) => updateField("min_account_balance", parseFloat(e.target.value))}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Stop trading if balance drops below this
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Max Trades Per Day
                        </label>
                        <Input
                          type="number"
                          value={formData.max_trades_per_day}
                          onChange={(e) => updateField("max_trades_per_day", parseInt(e.target.value))}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Limit number of trades per day
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Notifications */}
            <TabsContent value="notifications">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Bell className="h-5 w-5 text-primary" />
                    Discord Notifications
                  </CardTitle>
                  <CardDescription>
                    Get notified about trades and bot activity
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Enable Discord</p>
                      <p className="text-sm text-muted-foreground">
                        Send notifications to your Discord channel
                      </p>
                    </div>
                    <Switch
                      checked={discordEnabled}
                      onCheckedChange={setDiscordEnabled}
                    />
                  </div>

                  {discordEnabled && (
                    <div className="pt-4 border-t border-border space-y-4">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Webhook URL
                        </label>
                        <Input
                          type="password"
                          placeholder="https://discord.com/api/webhooks/..."
                          className="mt-1.5 bg-background font-mono"
                        />
                      </div>

                      <div className="space-y-3">
                        <p className="font-medium">Notify On</p>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Trade Executed</span>
                          <Switch
                            checked={notifyOnTrade}
                            onCheckedChange={setNotifyOnTrade}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Trade Skipped</span>
                          <Switch
                            checked={notifyOnSkip}
                            onCheckedChange={setNotifyOnSkip}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Errors</span>
                          <Switch
                            checked={notifyOnError}
                            onCheckedChange={setNotifyOnError}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* API Keys */}
            <TabsContent value="api">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="h-5 w-5 text-primary" />
                    API Configuration
                  </CardTitle>
                  <CardDescription>
                    API keys are managed server-side for security
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 rounded-lg bg-secondary/30 border border-border">
                    <p className="text-sm text-muted-foreground">
                      API keys for AI and trading integrations are configured on the server.
                      Contact @Kizsler if you need to modify API settings.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}

        {/* Save Button */}
        {user && !authLoading && (
          <div className="mt-8 flex justify-end gap-3">
            {saveSuccess && (
              <div className="flex items-center gap-2 text-profit">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm">Settings saved</span>
              </div>
            )}
            <Button className="gap-2" onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Settings
                </>
              )}
            </Button>
          </div>
        )}

        {/* Account Section */}
        {user && !authLoading && (
          <Card className="mt-8 bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LogOut className="h-5 w-5 text-muted-foreground" />
                Account
              </CardTitle>
              <CardDescription>
                Manage your account session
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Sign Out</p>
                  <p className="text-sm text-muted-foreground">
                    Log out of your account on this device
                  </p>
                </div>
                <Button
                  variant="outline"
                  className="gap-2 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-400"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                >
                  {isLoggingOut ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Signing out...
                    </>
                  ) : (
                    <>
                      <LogOut className="h-4 w-4" />
                      Sign Out
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ThreeColumnLayout>
  );
}
