"use client";

import { ThreeColumnLayout } from "@/components/layouts/three-column-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertCircle,
  AlertOctagon,
  Bell,
  Bot,
  CheckCircle,
  DollarSign,
  Key,
  Loader2,
  Play,
  Save,
  Shield,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { api, fetcher, Settings } from "@/lib/api";

export default function SettingsPage() {
  // Fetch settings from API
  const { data: settings, error, isLoading, mutate } = useSWR<Settings>(
    "/settings",
    fetcher
  );

  // Local state for form (initialized from API data)
  const [formData, setFormData] = useState<Partial<Settings>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Notification settings (local only for now)
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [notifyOnTrade, setNotifyOnTrade] = useState(true);
  const [notifyOnSkip, setNotifyOnSkip] = useState(false);
  const [notifyOnError, setNotifyOnError] = useState(true);

  // Emergency stop state
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);
  const [isStopLoading, setIsStopLoading] = useState(false);

  // Check emergency stop status on load
  useEffect(() => {
    api.getStatus().then((status) => {
      setIsEmergencyStopped(status.emergency_stop ?? false);
    }).catch(() => {});
  }, []);

  const handleEmergencyStop = async () => {
    setIsStopLoading(true);
    try {
      await api.emergencyStop();
      setIsEmergencyStopped(true);
    } catch (err) {
      console.error("Failed to activate emergency stop:", err);
    } finally {
      setIsStopLoading(false);
    }
  };

  const handleResumeTrading = async () => {
    setIsStopLoading(true);
    try {
      await api.resumeTrading();
      setIsEmergencyStopped(false);
    } catch (err) {
      console.error("Failed to resume trading:", err);
    } finally {
      setIsStopLoading(false);
    }
  };

  // Sync form data when settings load
  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await api.updateSettings(formData);
      await mutate();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const updateField = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

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

        {/* Error State */}
        {error && (
          <Card className="mb-8 bg-loss/10 border-loss/30">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-loss" />
                <div>
                  <p className="font-medium text-loss">API Connection Error</p>
                  <p className="text-sm text-muted-foreground">
                    Unable to load settings. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !settings && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading settings...</p>
              </div>
            </CardContent>
          </Card>
        )}

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
                    Choose between paper trading (simulated) or live trading
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
                    <Select
                      value={formData.trading_mode || "paper"}
                      onValueChange={(value) => updateField("trading_mode", value)}
                    >
                      <SelectTrigger className="w-40 bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="paper">
                          <span className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-profit" />
                            Paper
                          </span>
                        </SelectItem>
                        <SelectItem value="live">
                          <span className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-loss" />
                            Live
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {formData.trading_mode === "live" && (
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-loss/10 border border-loss/30">
                      <AlertCircle className="h-4 w-4 text-loss" />
                      <p className="text-sm text-loss">
                        Live trading uses real funds. Ensure you understand the risks.
                      </p>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-border">
                    <div>
                      <p className="font-medium">Auto-Trade</p>
                      <p className="text-sm text-muted-foreground">
                        Automatically execute AI-approved trades
                      </p>
                    </div>
                    <Switch
                      checked={formData.auto_trade ?? true}
                      onCheckedChange={(checked) => updateField("auto_trade", checked)}
                    />
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
                        Max Position Size ($)
                      </label>
                      <Input
                        type="number"
                        value={formData.max_position_size ?? 100}
                        onChange={(e) => updateField("max_position_size", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Maximum amount per single trade
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Max Daily Exposure ($)
                      </label>
                      <Input
                        type="number"
                        value={formData.max_daily_exposure ?? 2000}
                        onChange={(e) => updateField("max_daily_exposure", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Total open position limit per day
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
                    Configure how the AI evaluates and filters trades
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">AI Filtering</p>
                      <p className="text-sm text-muted-foreground">
                        Use AI to evaluate each trade before copying
                      </p>
                    </div>
                    <Switch
                      checked={formData.ai_enabled ?? true}
                      onCheckedChange={(checked) => updateField("ai_enabled", checked)}
                    />
                  </div>

                  {formData.ai_enabled && (
                    <div className="pt-4 border-t border-border">
                      <label className="text-sm font-medium text-muted-foreground">
                        Confidence Threshold
                      </label>
                      <Input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={formData.confidence_threshold ?? 0.70}
                        onChange={(e) => updateField("confidence_threshold", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Minimum AI confidence (0-1) required to copy a trade
                      </p>
                    </div>
                  )}
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
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    Market Filters
                  </CardTitle>
                  <CardDescription>
                    Control which markets the bot will trade on
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Min Probability
                      </label>
                      <Input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={formData.min_probability ?? 0.10}
                        onChange={(e) => updateField("min_probability", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Skip markets below this probability
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Max Probability
                      </label>
                      <Input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={formData.max_probability ?? 0.90}
                        onChange={(e) => updateField("max_probability", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Skip markets above this probability
                      </p>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-border">
                    <p className="font-medium mb-3">Category Filters</p>
                    <div className="flex flex-wrap gap-2">
                      {["Crypto", "Politics", "Sports", "Entertainment", "Science"].map(
                        (category) => (
                          <Badge
                            key={category}
                            variant="outline"
                            className="cursor-pointer hover:bg-primary/10 hover:border-primary/30"
                          >
                            {category}
                          </Badge>
                        )
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Click to enable/disable market categories
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>Loss Protection</CardTitle>
                  <CardDescription>
                    Automatic safeguards to protect your capital
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Daily Loss Limit ($)
                      </label>
                      <Input
                        type="number"
                        value={formData.daily_loss_limit ?? 500}
                        onChange={(e) => updateField("daily_loss_limit", parseFloat(e.target.value))}
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Stop trading if daily losses exceed this
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Max Consecutive Losses
                      </label>
                      <Input
                        type="number"
                        defaultValue="5"
                        className="mt-1.5 bg-background"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Pause after this many consecutive losses
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
                  API keys are configured via environment variables for security
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Claude API Key
                  </label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      type="password"
                      placeholder="Configured via ANTHROPIC_API_KEY"
                      disabled
                      className="bg-background font-mono"
                    />
                    <Badge variant="outline" className="text-profit border-profit/30">
                      Env Var
                    </Badge>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <label className="text-sm font-medium text-muted-foreground">
                    Polymarket API Key
                  </label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      type="password"
                      placeholder="Configured via POLYMARKET_API_KEY"
                      disabled
                      className="bg-background font-mono"
                    />
                    <Badge variant="outline" className="text-muted-foreground">
                      Env Var
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Set in .env file for security
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Save Button */}
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
      </div>
    </ThreeColumnLayout>
  );
}
