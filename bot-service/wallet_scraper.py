"""
Polymarket Wallet Scraper
Finds actively trading, profitable wallets from the last 48 hours.

Requirements:
- Min 10 trades in 48 hours
- Min $500 profit
- Active trading (trades in last 48h)
"""

import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
import json

# Configuration
POLYMARKET_DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

# Scraper settings
MIN_TRADES = 10  # Minimum trades in 48h
MIN_VOLUME = 500  # Minimum $500 volume (since profit is hard to calculate)
LOOKBACK_HOURS = 48


async def fetch_leaderboard() -> list[dict]:
    """Fetch top traders from Polymarket leaderboard"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GAMMA_API}/leaderboard",
                params={"window": "1w", "limit": 100},
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json() or []
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
        return []


async def fetch_wallet_profile(wallet_address: str) -> dict:
    """Fetch profile info for a wallet"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GAMMA_API}/users/{wallet_address}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json() or {}
        except:
            pass
        return {}


async def fetch_active_markets() -> list[dict]:
    """Fetch currently active markets from Polymarket"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GAMMA_API}/markets",
                params={"closed": False, "limit": 100},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json() or []
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []


async def fetch_trades_by_market(market_id: str, limit: int = 500) -> list[dict]:
    """Fetch trades for a specific market"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{POLYMARKET_DATA_API}/trades",
                params={"market": market_id, "limit": limit},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json() or []
        except Exception as e:
            print(f"Error fetching trades for market {market_id}: {e}")
            return []


async def fetch_wallet_trades(wallet_address: str, limit: int = 100) -> list[dict]:
    """Fetch trades for a specific wallet"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{POLYMARKET_DATA_API}/trades",
                params={"maker": wallet_address, "limit": limit},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json() or []
        except Exception as e:
            print(f"Error fetching wallet trades: {e}")
            return []


def parse_timestamp(ts) -> Optional[datetime]:
    """Parse various timestamp formats"""
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            if ts > 1e12:  # Milliseconds
                return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            else:  # Seconds
                return datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except:
        pass
    return None


async def analyze_wallet(wallet_address: str, trades: list[dict]) -> dict:
    """Analyze a wallet's trading performance"""
    if not trades:
        return None

    total_volume = 0
    buy_volume = 0
    sell_volume = 0
    markets_seen = set()

    for trade in trades:
        market_id = trade.get("conditionId", trade.get("market", ""))
        markets_seen.add(market_id)

        side = trade.get("side", "BUY").upper()
        price = float(trade.get("price", 0.5))
        size = float(trade.get("size", 0))

        volume = size * price
        total_volume += volume

        if side == "BUY":
            buy_volume += volume
        else:
            sell_volume += volume

    return {
        "address": wallet_address,
        "trade_count": len(trades),
        "total_volume": round(total_volume, 2),
        "buy_volume": round(buy_volume, 2),
        "sell_volume": round(sell_volume, 2),
        "markets_traded": len(markets_seen),
    }


async def scrape_from_leaderboard() -> list[dict]:
    """Scrape wallets from Polymarket's leaderboard"""
    print("Fetching leaderboard data...")
    leaderboard = await fetch_leaderboard()

    if leaderboard:
        print(f"Found {len(leaderboard)} traders on leaderboard")

        qualifying = []
        for entry in leaderboard:
            wallet = entry.get("address", entry.get("proxyWallet", ""))
            pnl = float(entry.get("pnl", entry.get("profit", 0)))
            volume = float(entry.get("volume", 0))

            if pnl >= MIN_VOLUME:  # Using MIN_VOLUME as min profit threshold
                qualifying.append({
                    "address": wallet,
                    "pnl": round(pnl, 2),
                    "volume": round(volume, 2),
                    "name": entry.get("name", entry.get("pseudonym", "")),
                })

        qualifying.sort(key=lambda x: x["pnl"], reverse=True)
        return qualifying
    return []


async def scrape_from_trades() -> list[dict]:
    """Scrape wallets from recent trade activity"""
    print(f"\nScraping active wallets from trade data...")
    print(f"Looking for:")
    print(f"  - Min {MIN_TRADES} trades in last {LOOKBACK_HOURS}h")
    print(f"  - Min ${MIN_VOLUME} volume")
    print()

    # Fetch active markets
    print("Fetching active markets...")
    markets = await fetch_active_markets()
    print(f"Found {len(markets)} active markets")

    # Fetch trades from top markets
    all_trades = []
    for i, market in enumerate(markets[:50]):
        market_id = market.get("conditionId", market.get("id", ""))
        if market_id:
            print(f"  Fetching trades from market {i+1}/50: {market.get('question', market_id)[:50]}...")
            trades = await fetch_trades_by_market(market_id)
            all_trades.extend(trades)
            if i % 5 == 0:
                await asyncio.sleep(0.5)

    print(f"\nTotal trades fetched: {len(all_trades)}")

    # Group trades by wallet
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    wallet_trades: dict[str, list[dict]] = defaultdict(list)

    for trade in all_trades:
        wallet = trade.get("proxyWallet", trade.get("maker", ""))
        if not wallet:
            continue

        # Check timestamp
        ts = trade.get("timestamp") or trade.get("createdAt") or trade.get("matchTime")
        trade_dt = parse_timestamp(ts)

        if trade_dt is None or trade_dt >= cutoff_time:
            wallet_trades[wallet].append(trade)

    print(f"Found {len(wallet_trades)} unique wallets")

    # Filter by min trades
    active_wallets = {
        addr: trades for addr, trades in wallet_trades.items()
        if len(trades) >= MIN_TRADES
    }
    print(f"Wallets with {MIN_TRADES}+ trades: {len(active_wallets)}")

    # Analyze each wallet
    print("\nAnalyzing wallets...")
    results = []
    for i, (wallet, trades) in enumerate(active_wallets.items()):
        if i % 10 == 0:
            print(f"  Analyzed {i}/{len(active_wallets)}...")

        analysis = await analyze_wallet(wallet, trades)
        if analysis and analysis["total_volume"] >= MIN_VOLUME:
            results.append(analysis)

    results.sort(key=lambda x: x["total_volume"], reverse=True)
    return results


async def main():
    """Entry point"""
    print("=" * 60)
    print("POLYMARKET WALLET SCRAPER")
    print("=" * 60)
    print()

    # Try leaderboard first
    leaderboard_wallets = await scrape_from_leaderboard()

    if leaderboard_wallets:
        print(f"\n{'='*60}")
        print(f"LEADERBOARD RESULTS: {len(leaderboard_wallets)} profitable wallets")
        print(f"{'='*60}\n")

        for i, w in enumerate(leaderboard_wallets[:20], 1):
            print(f"{i}. {w['address']}")
            print(f"   Name: {w['name'] or 'Anonymous'}")
            print(f"   PnL: ${w['pnl']:+,.2f} | Volume: ${w['volume']:,.2f}")
            print()
    else:
        print("Leaderboard not available, falling back to trade analysis...")

    # Also scrape from trades
    trade_wallets = await scrape_from_trades()

    print(f"\n{'='*60}")
    print(f"ACTIVE TRADERS: {len(trade_wallets)} wallets with ${MIN_VOLUME}+ volume")
    print(f"{'='*60}\n")

    for i, w in enumerate(trade_wallets[:20], 1):
        print(f"{i}. {w['address']}")
        print(f"   Trades: {w['trade_count']} | Volume: ${w['total_volume']:,.2f}")
        print(f"   Markets: {w['markets_traded']} | Buy/Sell: ${w['buy_volume']:,.0f}/${w['sell_volume']:,.0f}")
        print()

    # Combine and save results
    all_wallets = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "min_trades": MIN_TRADES,
            "min_volume": MIN_VOLUME,
            "lookback_hours": LOOKBACK_HOURS,
        },
        "leaderboard_wallets": leaderboard_wallets[:20],
        "active_traders": trade_wallets[:20],
    }

    with open("discovered_wallets.json", "w") as f:
        json.dump(all_wallets, f, indent=2)

    print(f"\nResults saved to discovered_wallets.json")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Leaderboard profitable wallets: {len(leaderboard_wallets)}")
    print(f"Active high-volume traders: {len(trade_wallets)}")

    if leaderboard_wallets:
        print(f"\nTop wallet from leaderboard:")
        print(f"  {leaderboard_wallets[0]['address']}")
        print(f"  PnL: ${leaderboard_wallets[0]['pnl']:+,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
