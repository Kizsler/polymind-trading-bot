"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
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
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  Filter,
  Shield,
  ShieldOff,
} from "lucide-react";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { api, fetcher, MarketFilter } from "@/lib/api";

export default function FiltersPage() {
  const [filterType, setFilterType] = useState<"market_id" | "category" | "keyword">("keyword");
  const [filterValue, setFilterValue] = useState("");
  const [filterAction, setFilterAction] = useState<"allow" | "deny">("deny");
  const [isAdding, setIsAdding] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: filters, error, isLoading } = useSWR<MarketFilter[]>(
    "/filters",
    fetcher,
    { refreshInterval: 30000 }
  );

  const handleAddFilter = async () => {
    if (!filterValue.trim()) return;

    setIsAdding(true);
    try {
      await api.addFilter({
        filter_type: filterType,
        value: filterValue.trim(),
        action: filterAction,
      });
      setFilterValue("");
      setDialogOpen(false);
      mutate("/filters");
    } catch (err) {
      console.error("Failed to add filter:", err);
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemoveFilter = async (id: number) => {
    try {
      await api.removeFilter(id);
      mutate("/filters");
    } catch (err) {
      console.error("Failed to remove filter:", err);
    }
  };

  const allowFilters = filters?.filter((f) => f.action === "allow") || [];
  const denyFilters = filters?.filter((f) => f.action === "deny") || [];

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Market Filters</h1>
            <p className="text-muted-foreground mt-1">
              Control which markets the bot can trade in
            </p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Add Filter
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-border">
              <DialogHeader>
                <DialogTitle>Add Market Filter</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Filter Type
                  </label>
                  <Select
                    value={filterType}
                    onValueChange={(v) => setFilterType(v as any)}
                  >
                    <SelectTrigger className="mt-1.5 bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="keyword">Keyword</SelectItem>
                      <SelectItem value="category">Category</SelectItem>
                      <SelectItem value="market_id">Market ID</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Value
                  </label>
                  <Input
                    placeholder={
                      filterType === "keyword"
                        ? "e.g., politics, sports"
                        : filterType === "category"
                        ? "e.g., crypto, elections"
                        : "e.g., 0x..."
                    }
                    value={filterValue}
                    onChange={(e) => setFilterValue(e.target.value)}
                    className="mt-1.5 bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Action
                  </label>
                  <Select
                    value={filterAction}
                    onValueChange={(v) => setFilterAction(v as any)}
                  >
                    <SelectTrigger className="mt-1.5 bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="deny">Deny (Block)</SelectItem>
                      <SelectItem value="allow">Allow (Whitelist)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  className="w-full"
                  onClick={handleAddFilter}
                  disabled={isAdding || !filterValue.trim()}
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Adding...
                    </>
                  ) : (
                    "Add Filter"
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
                    Unable to load filters. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !filters && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading filters...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{filters?.length || 0}</div>
              <p className="text-sm text-muted-foreground">Total Filters</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-profit">{allowFilters.length}</div>
              <p className="text-sm text-muted-foreground">Allow Rules</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-loss">{denyFilters.length}</div>
              <p className="text-sm text-muted-foreground">Deny Rules</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Active Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            {filters && filters.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  No filters configured. Add a filter to control which markets the bot can trade.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filters?.map((filter) => (
                    <TableRow key={filter.id}>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {filter.filter_type.replace("_", " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {filter.value}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            filter.action === "allow"
                              ? "text-profit border-profit/30"
                              : "text-loss border-loss/30"
                          }
                        >
                          {filter.action === "allow" ? (
                            <Shield className="h-3 w-3 mr-1" />
                          ) : (
                            <ShieldOff className="h-3 w-3 mr-1" />
                          )}
                          {filter.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(filter.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRemoveFilter(filter.id)}
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
    </DashboardLayout>
  );
}
