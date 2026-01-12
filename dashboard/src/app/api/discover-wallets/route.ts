import { NextResponse, NextRequest } from "next/server";

const POLYMARKET_DATA_API = "https://data-api.polymarket.com";
const GAMMA_API = "https://gamma-api.polymarket.com";

// Default values (can be overridden via query params)
const DEFAULT_MIN_TRADES = 10;
const DEFAULT_MIN_VOLUME = 500;
const DEFAULT_LOOKBACK_HOURS = 48;

interface Trade {
  proxyWallet?: string;
  maker?: string;
  side?: string;
  price?: number;
  size?: number;
  conditionId?: string;
  market?: string;
  timestamp?: number | string;
  title?: string;
  outcome?: string;
}

interface WalletAnalysis {
  address: string;
  trade_count: number;
  total_volume: number;
  buy_volume: number;
  sell_volume: number;
  markets_traded: number;
  avg_buy_price: number;
  avg_sell_price: number;
  estimated_pnl: number;
  is_profitable: boolean;
}

async function fetchActiveMarkets(): Promise<any[]> {
  try {
    const response = await fetch(`${GAMMA_API}/markets?closed=false&limit=100`, {
      next: { revalidate: 300 }, // Cache for 5 minutes
    });
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.error("Error fetching markets:", e);
  }
  return [];
}

async function fetchTradesByMarket(marketId: string): Promise<Trade[]> {
  try {
    const response = await fetch(
      `${POLYMARKET_DATA_API}/trades?market=${marketId}&limit=500`,
      { next: { revalidate: 60 } }
    );
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.error(`Error fetching trades for ${marketId}:`, e);
  }
  return [];
}

// Fetch a wallet's full trade history to calculate actual PnL
async function fetchWalletTrades(walletAddress: string): Promise<Trade[]> {
  try {
    const response = await fetch(
      `${POLYMARKET_DATA_API}/trades?maker=${walletAddress}&limit=200`,
      { next: { revalidate: 60 } }
    );
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.error(`Error fetching wallet trades for ${walletAddress}:`, e);
  }
  return [];
}

function parseTimestamp(ts: number | string | undefined): Date | null {
  if (!ts) return null;
  try {
    if (typeof ts === "number") {
      return new Date(ts > 1e12 ? ts : ts * 1000);
    } else if (typeof ts === "string") {
      return new Date(ts);
    }
  } catch {
    return null;
  }
  return null;
}

function analyzeWallet(trades: Trade[]): WalletAnalysis | null {
  if (!trades.length) return null;

  const wallet = trades[0].proxyWallet || trades[0].maker || "";
  let totalVolume = 0;
  let buyVolume = 0;
  let sellVolume = 0;
  let buyCount = 0;
  let sellCount = 0;
  let totalBuyPrice = 0;
  let totalSellPrice = 0;
  const marketsSeen = new Set<string>();

  // Group trades by market to calculate PnL
  const marketTrades: Record<string, { buys: { price: number; size: number }[]; sells: { price: number; size: number }[] }> = {};

  for (const trade of trades) {
    const marketId = trade.conditionId || trade.market || "";
    marketsSeen.add(marketId);

    const side = (trade.side || "BUY").toUpperCase();
    const price = trade.price || 0.5;
    const size = trade.size || 0;
    const volume = size * price;

    totalVolume += volume;

    if (!marketTrades[marketId]) {
      marketTrades[marketId] = { buys: [], sells: [] };
    }

    if (side === "BUY") {
      buyVolume += volume;
      buyCount++;
      totalBuyPrice += price;
      marketTrades[marketId].buys.push({ price, size });
    } else {
      sellVolume += volume;
      sellCount++;
      totalSellPrice += price;
      marketTrades[marketId].sells.push({ price, size });
    }
  }

  // Calculate estimated PnL based on matched buys/sells per market
  let estimatedPnl = 0;
  let hasMatchedTrades = false;

  for (const market of Object.values(marketTrades)) {
    // If we have both buys and sells in the same market, calculate actual PnL
    if (market.sells.length > 0 && market.buys.length > 0) {
      hasMatchedTrades = true;
      const avgBuy = market.buys.reduce((sum, t) => sum + t.price, 0) / market.buys.length;
      const avgSell = market.sells.reduce((sum, t) => sum + t.price, 0) / market.sells.length;
      const matchedSize = Math.min(
        market.buys.reduce((sum, t) => sum + t.size, 0),
        market.sells.reduce((sum, t) => sum + t.size, 0)
      );
      estimatedPnl += (avgSell - avgBuy) * matchedSize;
    }
  }

  const avgBuyPrice = buyCount > 0 ? totalBuyPrice / buyCount : 0;
  const avgSellPrice = sellCount > 0 ? totalSellPrice / sellCount : 0;

  // Determine profitability:
  // 1. If we have matched trades, use actual PnL
  // 2. If only sells (taking profits from earlier buys), consider profitable if selling at good prices (>0.6)
  // 3. If only buys, not yet profitable (still holding)
  let isProfitable = false;
  if (hasMatchedTrades) {
    isProfitable = estimatedPnl > 0;
  } else if (sellCount > 0 && buyCount === 0) {
    // Only sells - they're taking profits from earlier positions
    // Consider profitable if average sell price is decent (selling winners)
    isProfitable = avgSellPrice > 0.55;
    estimatedPnl = sellVolume * (avgSellPrice - 0.5); // Rough estimate assuming avg cost of 0.5
  } else if (buyCount > 0 && sellCount === 0) {
    // Only buys - unrealized, check if they're buying at good prices
    isProfitable = false; // Can't determine yet, they're still holding
    estimatedPnl = 0;
  }

  return {
    address: wallet,
    trade_count: trades.length,
    total_volume: Math.round(totalVolume * 100) / 100,
    buy_volume: Math.round(buyVolume * 100) / 100,
    sell_volume: Math.round(sellVolume * 100) / 100,
    markets_traded: marketsSeen.size,
    avg_buy_price: Math.round(avgBuyPrice * 1000) / 1000,
    avg_sell_price: Math.round(avgSellPrice * 1000) / 1000,
    estimated_pnl: Math.round(estimatedPnl * 100) / 100,
    is_profitable: isProfitable,
  };
}

export async function GET(request: NextRequest) {
  try {
    // Parse query parameters
    const searchParams = request.nextUrl.searchParams;
    const minTradesParam = searchParams.get("min_trades");
    const minVolumeParam = searchParams.get("min_volume");
    const lookbackParam = searchParams.get("lookback_hours");

    const MIN_TRADES = minTradesParam !== null ? parseInt(minTradesParam) : DEFAULT_MIN_TRADES;
    const MIN_VOLUME = minVolumeParam !== null ? parseInt(minVolumeParam) : DEFAULT_MIN_VOLUME;
    const LOOKBACK_HOURS = Math.min(
      lookbackParam !== null ? parseInt(lookbackParam) : DEFAULT_LOOKBACK_HOURS,
      168 // Max 7 days
    );
    const PROFITABLE_ONLY = searchParams.get("profitable_only") === "true";

    // Fetch active markets
    const markets = await fetchActiveMarkets();

    // Fetch trades from top 30 markets (reduced for speed)
    const allTrades: Trade[] = [];
    const marketPromises = markets.slice(0, 30).map(async (market) => {
      const marketId = market.conditionId || market.id;
      if (marketId) {
        const trades = await fetchTradesByMarket(marketId);
        return trades;
      }
      return [];
    });

    const marketTrades = await Promise.all(marketPromises);
    for (const trades of marketTrades) {
      allTrades.push(...trades);
    }

    // Group trades by wallet
    const cutoffTime = new Date(Date.now() - LOOKBACK_HOURS * 60 * 60 * 1000);
    const walletTrades: Record<string, Trade[]> = {};

    for (const trade of allTrades) {
      const wallet = trade.proxyWallet || trade.maker;
      if (!wallet) continue;

      const tradeTime = parseTimestamp(trade.timestamp);
      if (tradeTime === null || tradeTime >= cutoffTime) {
        if (!walletTrades[wallet]) {
          walletTrades[wallet] = [];
        }
        walletTrades[wallet].push(trade);
      }
    }

    // First pass: identify candidate wallets by activity
    const candidates: { address: string; tradeCount: number; volume: number }[] = [];

    for (const [wallet, trades] of Object.entries(walletTrades)) {
      if (trades.length >= MIN_TRADES) {
        const volume = trades.reduce((sum, t) => sum + (t.size || 0) * (t.price || 0.5), 0);
        if (volume >= MIN_VOLUME) {
          candidates.push({ address: wallet, tradeCount: trades.length, volume });
        }
      }
    }

    // Analyze all wallets with their trades
    const results: WalletAnalysis[] = [];

    for (const [wallet, trades] of Object.entries(walletTrades)) {
      if (trades.length >= MIN_TRADES) {
        const analysis = analyzeWallet(trades);
        if (analysis && analysis.total_volume >= MIN_VOLUME) {
          // Apply profitable filter if enabled
          if (PROFITABLE_ONLY && !analysis.is_profitable) {
            continue;
          }
          results.push(analysis);
        }
      }
    }

    // Sort by PnL (most profitable first), then by volume
    results.sort((a, b) => {
      if (b.estimated_pnl !== a.estimated_pnl) {
        return b.estimated_pnl - a.estimated_pnl;
      }
      return b.total_volume - a.total_volume;
    });

    return NextResponse.json({
      success: true,
      criteria: {
        min_trades: MIN_TRADES,
        min_volume: MIN_VOLUME,
        lookback_hours: LOOKBACK_HOURS,
      },
      total_trades_analyzed: allTrades.length,
      unique_wallets: Object.keys(walletTrades).length,
      qualifying_wallets: results.length,
      wallets: results.slice(0, 50), // Top 50
    });
  } catch (error) {
    console.error("Scraper error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to scrape wallets" },
      { status: 500 }
    );
  }
}
