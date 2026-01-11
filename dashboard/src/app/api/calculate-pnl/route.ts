import { NextResponse } from "next/server";

const CLOB_API_URL = "https://clob.polymarket.com";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Trade {
  id: string;
  market_id: string;
  side: "YES" | "NO";
  size: number;
  price: number;
  executed: boolean;
  pnl: number | null;
}

interface MarketData {
  closed: boolean;
  tokens: Array<{
    outcome: string;
    winner: boolean;
  }>;
  question: string;
}

function mapOutcomeToSide(outcome: string): "YES" | "NO" {
  const lower = outcome.toLowerCase();
  return lower === "yes" || lower === "up" ? "YES" : "NO";
}

export async function POST() {
  try {
    // Get trades from our API
    const tradesResponse = await fetch(`${API_BASE}/trades?limit=500&executed_only=true`);
    if (!tradesResponse.ok) {
      return NextResponse.json({ error: "Failed to fetch trades" }, { status: 500 });
    }
    const trades: Trade[] = await tradesResponse.json();

    // Filter trades without PnL
    const pendingTrades = trades.filter((t) => t.pnl === null);
    if (pendingTrades.length === 0) {
      // Get summary of existing PnL
      const tradesWithPnl = trades.filter((t) => t.pnl !== null);
      const totalPnl = tradesWithPnl.reduce((sum, t) => sum + (t.pnl || 0), 0);
      const wins = tradesWithPnl.filter((t) => (t.pnl || 0) > 0);

      return NextResponse.json({
        message: "All trades already have PnL calculated",
        updated: 0,
        total_pnl: totalPnl.toFixed(2),
        win_count: wins.length,
        loss_count: tradesWithPnl.length - wins.length,
        win_rate: tradesWithPnl.length > 0 ? ((wins.length / tradesWithPnl.length) * 100).toFixed(1) : 0,
      });
    }

    // Get unique market IDs
    const marketIds = [...new Set(pendingTrades.map((t) => t.market_id))];

    // Fetch market data
    const marketData: Record<string, MarketData> = {};
    for (const marketId of marketIds) {
      try {
        const response = await fetch(`${CLOB_API_URL}/markets/${marketId}`);
        if (response.ok) {
          marketData[marketId] = await response.json();
        }
      } catch {
        // Skip failed fetches
      }
    }

    // Calculate PnL for each trade
    const results: Array<{ id: string; pnl: number; market: string; side: string; won: boolean }> = [];

    for (const trade of pendingTrades) {
      const market = marketData[trade.market_id];
      if (!market || !market.closed) continue;

      // Find winner
      let winningSide: "YES" | "NO" | null = null;
      for (const token of market.tokens) {
        if (token.winner) {
          winningSide = mapOutcomeToSide(token.outcome);
          break;
        }
      }

      if (!winningSide) continue;

      // Calculate PnL
      // Winner gets $1 per share, loser gets $0
      const won = trade.side === winningSide;
      const pnl = won ? trade.size * (1 - trade.price) : -trade.size * trade.price;

      results.push({
        id: trade.id,
        pnl: Math.round(pnl * 100) / 100,
        market: market.question?.slice(0, 50) || trade.market_id.slice(0, 20),
        side: trade.side,
        won,
      });
    }

    // Calculate totals
    const totalPnl = results.reduce((sum, r) => sum + r.pnl, 0);
    const wins = results.filter((r) => r.won);
    const losses = results.filter((r) => !r.won);

    return NextResponse.json({
      message: `Calculated PnL for ${results.length} resolved trades`,
      calculated: results.length,
      pending: pendingTrades.length - results.length,
      total_pnl: totalPnl.toFixed(2),
      win_count: wins.length,
      loss_count: losses.length,
      win_rate: results.length > 0 ? ((wins.length / results.length) * 100).toFixed(1) : 0,
      total_won: wins.reduce((sum, r) => sum + r.pnl, 0).toFixed(2),
      total_lost: losses.reduce((sum, r) => sum + r.pnl, 0).toFixed(2),
      details: results.slice(0, 30), // First 30 for display
    });
  } catch (error) {
    console.error("PnL calculation error:", error);
    return NextResponse.json({ error: "Failed to calculate PnL" }, { status: 500 });
  }
}
