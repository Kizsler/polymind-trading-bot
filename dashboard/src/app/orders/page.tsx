"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  Loader2,
  AlertCircle,
  ClipboardList,
  XCircle,
  CheckCircle,
  Clock,
  AlertTriangle,
  RotateCw,
} from "lucide-react";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { api, fetcher, Order } from "@/lib/api";

const statusConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  pending: { icon: Clock, color: "text-muted-foreground", label: "Pending" },
  submitted: { icon: RotateCw, color: "text-primary", label: "Submitted" },
  filled: { icon: CheckCircle, color: "text-profit", label: "Filled" },
  partial: { icon: AlertTriangle, color: "text-warning", label: "Partial" },
  failed: { icon: XCircle, color: "text-loss", label: "Failed" },
  cancelled: { icon: XCircle, color: "text-muted-foreground", label: "Cancelled" },
};

export default function OrdersPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: orders, error, isLoading } = useSWR<Order[]>(
    `/orders?${statusFilter !== "all" ? `status=${statusFilter}&` : ""}limit=100`,
    fetcher,
    { refreshInterval: 5000 }
  );

  const handleCancelOrder = async (id: number) => {
    try {
      await api.cancelOrder(id);
      mutate(`/orders?${statusFilter !== "all" ? `status=${statusFilter}&` : ""}limit=100`);
    } catch (err) {
      console.error("Failed to cancel order:", err);
    }
  };

  const pendingOrders = orders?.filter((o) => o.status === "pending" || o.status === "submitted") || [];
  const filledOrders = orders?.filter((o) => o.status === "filled" || o.status === "partial") || [];
  const failedOrders = orders?.filter((o) => o.status === "failed" || o.status === "cancelled") || [];

  const totalFilled = filledOrders.reduce((acc, o) => acc + o.filled_size, 0);

  return (
    <DashboardLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Orders</h1>
            <p className="text-muted-foreground mt-1">
              Track order lifecycle and execution status
            </p>
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px] bg-background">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Orders</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="submitted">Submitted</SelectItem>
              <SelectItem value="filled">Filled</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
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
                    Unable to load orders. Make sure the API server is running.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && !orders && (
          <Card className="mb-8 bg-secondary/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-muted-foreground">Loading orders...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{orders?.length || 0}</div>
              <p className="text-sm text-muted-foreground">Total Orders</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-primary">{pendingOrders.length}</div>
              <p className="text-sm text-muted-foreground">Pending</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-profit">{filledOrders.length}</div>
              <p className="text-sm text-muted-foreground">Filled</p>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-loss">{failedOrders.length}</div>
              <p className="text-sm text-muted-foreground">Failed</p>
            </CardContent>
          </Card>
        </div>

        {/* Orders Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Order History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {orders && orders.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  No orders found. Orders will appear here when trades are executed.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Market</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Requested</TableHead>
                    <TableHead className="text-right">Filled</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orders?.map((order) => {
                    const status = statusConfig[order.status] || statusConfig.pending;
                    const StatusIcon = status.icon;
                    return (
                      <TableRow key={order.id}>
                        <TableCell className="font-mono text-xs">
                          #{order.id}
                        </TableCell>
                        <TableCell className="font-mono text-xs max-w-[150px] truncate">
                          {order.market_id.slice(0, 20)}...
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={
                              order.side === "BUY"
                                ? "text-profit border-profit/30"
                                : "text-loss border-loss/30"
                            }
                          >
                            {order.side}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <StatusIcon className={`h-4 w-4 ${status.color}`} />
                            <span className={status.color}>{status.label}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          ${order.requested_size.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          ${order.filled_size.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {order.filled_price ? `$${order.filled_price.toFixed(2)}` : "-"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {new Date(order.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {(order.status === "pending" || order.status === "submitted") && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleCancelOrder(order.id)}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}

            {/* Failure Details */}
            {orders?.some((o) => o.failure_reason) && (
              <div className="mt-6 pt-6 border-t border-border">
                <h3 className="text-sm font-medium mb-4">Recent Failures</h3>
                <div className="space-y-2">
                  {orders
                    .filter((o) => o.failure_reason)
                    .slice(0, 5)
                    .map((order) => (
                      <div
                        key={order.id}
                        className="p-3 rounded-lg bg-loss/10 border border-loss/20"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-sm">Order #{order.id}</span>
                          <span className="text-xs text-muted-foreground">
                            Attempt {order.attempts}/{order.max_attempts}
                          </span>
                        </div>
                        <p className="text-sm text-loss mt-1">{order.failure_reason}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
