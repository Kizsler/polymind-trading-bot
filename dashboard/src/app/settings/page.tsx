"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
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
  Bell,
  Bot,
  DollarSign,
  Key,
  Save,
  Shield,
  Zap,
} from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  // Trading settings
  const [tradingMode, setTradingMode] = useState("paper");
  const [maxPositionSize, setMaxPositionSize] = useState("100");
  const [maxDailyExposure, setMaxDailyExposure] = useState("2000");
  const [minProbability, setMinProbability] = useState("0.10");
  const [maxProbability, setMaxProbability] = useState("0.90");
  const [autoTrade, setAutoTrade] = useState(true);

  // AI settings
  const [aiEnabled, setAiEnabled] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState("0.70");
  const [reasoningModel, setReasoningModel] = useState("claude-sonnet");

  // Notification settings
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [notifyOnTrade, setNotifyOnTrade] = useState(true);
  const [notifyOnSkip, setNotifyOnSkip] = useState(false);
  const [notifyOnError, setNotifyOnError] = useState(true);

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Configure your trading bot parameters and preferences
          </p>
        </div>

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
                    <Select value={tradingMode} onValueChange={setTradingMode}>
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

                  {tradingMode === "live" && (
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
                    <Switch checked={autoTrade} onCheckedChange={setAutoTrade} />
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
                        value={maxPositionSize}
                        onChange={(e) => setMaxPositionSize(e.target.value)}
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
                        value={maxDailyExposure}
                        onChange={(e) => setMaxDailyExposure(e.target.value)}
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
                    <Switch checked={aiEnabled} onCheckedChange={setAiEnabled} />
                  </div>

                  {aiEnabled && (
                    <>
                      <div className="pt-4 border-t border-border">
                        <label className="text-sm font-medium text-muted-foreground">
                          Reasoning Model
                        </label>
                        <Select value={reasoningModel} onValueChange={setReasoningModel}>
                          <SelectTrigger className="mt-1.5 bg-background">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="claude-sonnet">Claude Sonnet (Fast)</SelectItem>
                            <SelectItem value="claude-opus">Claude Opus (Best)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Confidence Threshold
                        </label>
                        <Input
                          type="number"
                          step="0.05"
                          min="0"
                          max="1"
                          value={confidenceThreshold}
                          onChange={(e) => setConfidenceThreshold(e.target.value)}
                          className="mt-1.5 bg-background"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Minimum AI confidence (0-1) required to copy a trade
                        </p>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Risk Limits */}
          <TabsContent value="risk">
            <div className="grid gap-6">
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
                        value={minProbability}
                        onChange={(e) => setMinProbability(e.target.value)}
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
                        value={maxProbability}
                        onChange={(e) => setMaxProbability(e.target.value)}
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
                        defaultValue="500"
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
                  Manage your API keys and credentials
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
                      placeholder="sk-ant-..."
                      className="bg-background font-mono"
                    />
                    <Badge variant="outline" className="text-profit border-profit/30">
                      Connected
                    </Badge>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <label className="text-sm font-medium text-muted-foreground">
                    Polymarket API Key (Optional)
                  </label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      type="password"
                      placeholder="Enter API key for live trading"
                      className="bg-background font-mono"
                    />
                    <Badge variant="outline" className="text-muted-foreground">
                      Not Set
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Required for live trading mode
                  </p>
                </div>

                <div className="pt-4 border-t border-border">
                  <label className="text-sm font-medium text-muted-foreground">
                    Polymarket Private Key
                  </label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      type="password"
                      placeholder="0x..."
                      className="bg-background font-mono"
                    />
                    <Badge variant="outline" className="text-muted-foreground">
                      Not Set
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Your wallet private key for executing trades
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Save Button */}
        <div className="mt-8 flex justify-end">
          <Button className="gap-2">
            <Save className="h-4 w-4" />
            Save Settings
          </Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
