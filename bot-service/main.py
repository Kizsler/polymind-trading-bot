"""
PolyMind Multi-Tenant Bot Service
Runs on server, handles all users automatically
Includes real-time PnL calculation with proper buy/sell tracking
"""
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, TypedDict
import json
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client
import anthropic

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("polymind-bot")

# Configuration from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
POLYMARKET_DATA_API = "https://data-api.polymarket.com"
POLYMARKET_CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))
PNL_UPDATE_INTERVAL = int(os.environ.get("PNL_UPDATE_INTERVAL", "60"))
AI_EVAL_INTERVAL = int(os.environ.get("AI_EVAL_INTERVAL", "300"))  # 5 minutes default
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Track processed trades to avoid duplicates
processed_trades: set[str] = set()
# Cache for market prices
market_price_cache: dict[str, dict] = {}
# Cache for user open positions (user_id -> market_id -> position)
user_positions_cache: dict[str, dict[str, dict]] = {}
# Cache for whale positions (wallet:market_id -> position data)
whale_position_cache: dict[str, dict] = {}
# Cache for market metadata (market_id -> metadata)
market_metadata_cache: dict[str, dict] = {}
# Track last AI evaluation time per position
last_ai_eval: dict[str, datetime] = {}
# Track positions flagged for immediate evaluation
urgent_eval_queue: set[str] = set()  # Set of "user_id:trade_id" keys
# Previous price cache for detecting big moves
previous_prices: dict[str, float] = {}  # market_id -> last_price


def get_supabase() -> Client:
    """Create Supabase client with service role key"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def get_active_users(supabase: Client) -> list[dict]:
    """Get all users with active (running) bots"""
    response = supabase.table("profiles").select("*").eq("bot_status", "running").execute()
    return response.data or []


async def get_user_open_positions(supabase: Client, user_id: str) -> dict[str, dict]:
    """Get user's open positions from the database"""
    # Check cache first
    if user_id in user_positions_cache:
        return user_positions_cache[user_id]

    # Query open positions (trades that haven't been closed)
    response = supabase.table("trades").select("*").eq(
        "user_id", user_id
    ).eq("executed", True).eq("is_closed", False).execute()

    positions = {}
    for trade in (response.data or []):
        market_id = trade.get("market_id", "")
        side = trade.get("side", "YES")
        key = f"{market_id}:{side}"

        if key not in positions:
            positions[key] = {
                "market_id": market_id,
                "side": side,
                "total_size": 0,
                "avg_entry_price": 0,
                "trade_ids": [],
                "total_cost": 0
            }

        size = float(trade.get("size", 0))
        price = float(trade.get("price", 0))
        positions[key]["total_size"] += size
        positions[key]["total_cost"] += size * price
        positions[key]["trade_ids"].append(trade.get("id"))

        # Recalculate average entry price
        if positions[key]["total_size"] > 0:
            positions[key]["avg_entry_price"] = positions[key]["total_cost"] / positions[key]["total_size"]

    user_positions_cache[user_id] = positions
    return positions


def invalidate_position_cache(user_id: str):
    """Clear position cache for a user"""
    if user_id in user_positions_cache:
        del user_positions_cache[user_id]


async def get_user_wallets(supabase: Client, user_id: str) -> list[str]:
    """Get all wallet addresses a user is tracking"""
    wallets = []

    # Get recommended wallet selections
    selections = supabase.table("user_recommended_selections").select(
        "wallet_id, recommended_wallets(address)"
    ).eq("user_id", user_id).eq("enabled", True).execute()

    for selection in (selections.data or []):
        if selection.get("recommended_wallets", {}).get("address"):
            wallets.append(selection["recommended_wallets"]["address"])

    # Get custom wallets
    custom = supabase.table("user_wallets").select("address").eq(
        "user_id", user_id
    ).eq("enabled", True).execute()

    for wallet in (custom.data or []):
        if wallet.get("address"):
            wallets.append(wallet["address"])

    return list(set(wallets))


async def fetch_market_price(market_id: str) -> Optional[dict]:
    """Fetch current market price from Polymarket"""
    # Check cache first (valid for 30 seconds)
    if market_id in market_price_cache:
        cached = market_price_cache[market_id]
        if datetime.utcnow() - cached["fetched_at"] < timedelta(seconds=30):
            return cached

    async with httpx.AsyncClient() as client:
        try:
            # Try CLOB API for live prices
            response = await client.get(
                f"{POLYMARKET_CLOB_API}/markets/{market_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                result = {
                    "market_id": market_id,
                    "yes_price": float(data.get("bestAsk", data.get("lastTradePrice", 0.5))),
                    "no_price": 1.0 - float(data.get("bestAsk", data.get("lastTradePrice", 0.5))),
                    "resolved": data.get("closed", False),
                    "resolution": data.get("winner"),  # "Yes", "No", or None
                    "fetched_at": datetime.utcnow()
                }
                market_price_cache[market_id] = result
                return result
        except Exception as e:
            logger.debug(f"CLOB API failed for {market_id}: {e}")

        try:
            # Fallback to Gamma API
            response = await client.get(
                f"{GAMMA_API}/markets/{market_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                yes_price = float(data.get("outcomePrices", [0.5, 0.5])[0])
                result = {
                    "market_id": market_id,
                    "yes_price": yes_price,
                    "no_price": 1.0 - yes_price,
                    "resolved": data.get("closed", False),
                    "resolution": data.get("winner"),
                    "fetched_at": datetime.utcnow()
                }
                market_price_cache[market_id] = result
                return result
        except Exception as e:
            logger.debug(f"Gamma API failed for {market_id}: {e}")

    return None


async def fetch_wallet_trades(wallet_address: str) -> list[dict]:
    """Fetch recent trades from a wallet via Polymarket Data API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{POLYMARKET_DATA_API}/trades",
                params={
                    "maker": wallet_address,
                    "limit": 50
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json() or []
        except Exception as e:
            logger.warning(f"Failed to fetch trades for {wallet_address[:10]}...: {e}")
            return []


def calculate_pnl(trade: dict, market_data: dict) -> float:
    """
    Calculate PnL for a trade based on current market price.

    For prediction markets:
    - Buy YES at $0.40, current YES price $0.60 -> PnL = (0.60 - 0.40) * size
    - Buy NO at $0.40, current NO price $0.60 -> PnL = (0.60 - 0.40) * size
    - If resolved to YES: YES position worth $1, NO position worth $0
    - If resolved to NO: NO position worth $1, YES position worth $0
    """
    entry_price = float(trade.get("price", 0.5))
    size = float(trade.get("size", 0))
    side = trade.get("side", "YES").upper()

    if market_data.get("resolved"):
        # Market resolved - calculate final PnL
        resolution = market_data.get("resolution", "").lower()
        if resolution == "yes":
            final_price = 1.0 if side == "YES" else 0.0
        elif resolution == "no":
            final_price = 0.0 if side == "YES" else 1.0
        else:
            # Unknown resolution, use current price
            final_price = market_data.get("yes_price", 0.5) if side == "YES" else market_data.get("no_price", 0.5)
    else:
        # Market still open - use current price for unrealized PnL
        final_price = market_data.get("yes_price", 0.5) if side == "YES" else market_data.get("no_price", 0.5)

    # PnL = (current_price - entry_price) * size
    pnl = (final_price - entry_price) * size
    return round(pnl, 2)


async def update_trade_pnl(supabase: Client):
    """Update PnL for all open trades based on current market prices"""
    try:
        # Get all trades that need PnL updates
        response = supabase.table("trades").select("*").eq("executed", True).execute()
        trades = response.data or []

        if not trades:
            return

        # Group trades by market_id for efficient API calls
        markets: dict[str, list[dict]] = {}
        for trade in trades:
            market_id = trade.get("market_id", "")
            if market_id:
                if market_id not in markets:
                    markets[market_id] = []
                markets[market_id].append(trade)

        logger.info(f"Updating PnL for {len(trades)} trades across {len(markets)} markets")

        updated_count = 0
        for market_id, market_trades in markets.items():
            market_data = await fetch_market_price(market_id)
            if not market_data:
                continue

            for trade in market_trades:
                new_pnl = calculate_pnl(trade, market_data)
                old_pnl = trade.get("pnl", 0)

                # Only update if PnL changed significantly (more than $0.01)
                if abs(new_pnl - (old_pnl or 0)) > 0.01:
                    try:
                        # Try full update first
                        supabase.table("trades").update({
                            "pnl": new_pnl,
                            "current_price": market_data.get("yes_price") if trade.get("side") == "YES" else market_data.get("no_price"),
                            "is_resolved": market_data.get("resolved", False)
                        }).eq("id", trade["id"]).execute()
                        updated_count += 1
                    except Exception as e:
                        # Fallback: just update PnL if new columns don't exist
                        try:
                            supabase.table("trades").update({
                                "pnl": new_pnl
                            }).eq("id", trade["id"]).execute()
                            updated_count += 1
                        except Exception as e2:
                            logger.error(f"Failed to update trade {trade['id']}: {e2}")

        if updated_count > 0:
            logger.info(f"Updated PnL for {updated_count} trades")

    except Exception as e:
        logger.error(f"Error updating PnL: {e}")


async def process_trade_for_user(
    supabase: Client,
    user: dict,
    trade: dict,
    whale_wallet: str
) -> Optional[dict]:
    """Process a whale trade for a specific user (paper trading with buy/sell support)"""
    user_id = user["id"]

    # Create unique trade ID
    trade_id = f"{user_id}:{trade.get('id', trade.get('transactionHash', ''))}"

    # Skip if already processed
    if trade_id in processed_trades:
        return None

    processed_trades.add(trade_id)

    # Determine if this is a BUY or SELL action
    action = trade.get("side", "BUY").upper()
    is_sell = action == "SELL"

    # Determine the position direction (YES or NO)
    outcome = trade.get("outcome", "").lower()
    if outcome == "yes":
        position_side = "YES"
    elif outcome == "no":
        position_side = "NO"
    elif action in ["YES", "NO"]:
        position_side = action
    else:
        position_side = "YES"  # Default

    # Get market info
    market_id = trade.get("market", trade.get("conditionId", ""))
    trade_price = float(trade.get("price", 0.5))

    # Calculate paper trade size based on user's copy_percentage
    copy_pct = user.get("copy_percentage", 0.1)
    whale_size = float(trade.get("size", trade.get("amount", 0)))
    our_size = whale_size * copy_pct

    # Get user's starting balance
    starting_balance = user.get("starting_balance", 1000)

    # Check if trade size is within limits (max 5% of starting balance per trade)
    # This prevents any single position from causing catastrophic losses
    max_trade_size = starting_balance * 0.05
    our_size = min(our_size, max_trade_size)

    if our_size < 1:  # Minimum trade size
        return None

    if is_sell:
        # ========== SELL/CLOSE POSITION ==========
        return await close_position_for_user(
            supabase, user, market_id, position_side, our_size, trade_price, whale_wallet, trade
        )
    else:
        # ========== BUY/OPEN POSITION ==========
        return await open_position_for_user(
            supabase, user, market_id, position_side, our_size, trade_price, whale_wallet, trade
        )


async def open_position_for_user(
    supabase: Client,
    user: dict,
    market_id: str,
    side: str,
    size: float,
    entry_price: float,
    whale_wallet: str,
    trade: dict
) -> Optional[dict]:
    """Open a new paper position (BUY)"""
    user_id = user["id"]

    # Fetch current market price for initial PnL calculation
    market_data = await fetch_market_price(market_id)
    initial_pnl = 0.0
    current_price = entry_price

    if market_data:
        current_price = market_data.get("yes_price", entry_price) if side == "YES" else market_data.get("no_price", entry_price)
        # Calculate initial unrealized PnL
        initial_pnl = (current_price - entry_price) * size

    # Create paper trade record for opening position
    paper_trade = {
        "user_id": user_id,
        "wallet_address": whale_wallet,
        "market_id": market_id,
        "market_title": trade.get("marketSlug", trade.get("question", f"Market {market_id[:8]}")),
        "wallet": whale_wallet,
        "wallet_alias": f"Whale {whale_wallet[:6]}",
        "side": side,
        "action": "BUY",
        "size": size,
        "price": entry_price,
        "executed": True,
        "is_closed": False,
        "pnl": round(initial_pnl, 2),
        "realized_pnl": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "whale_trade_id": trade.get("id", trade.get("transactionHash", "")),
    }

    # Save to Supabase
    try:
        full_trade = {**paper_trade, "current_price": current_price, "is_resolved": False}
        supabase.table("trades").insert(full_trade).execute()
        invalidate_position_cache(user_id)
        logger.info(f"📈 OPEN {side} for user {user_id[:8]}: ${size:.2f} @ ${entry_price:.2f} on {market_id[:8]}")
        return paper_trade
    except Exception as e:
        # Fallback without new columns
        try:
            supabase.table("trades").insert(paper_trade).execute()
            invalidate_position_cache(user_id)
            logger.info(f"📈 OPEN {side} for user {user_id[:8]}: ${size:.2f} @ ${entry_price:.2f} on {market_id[:8]}")
            return paper_trade
        except Exception as e2:
            logger.error(f"Failed to save open trade: {e2}")
            return None


async def close_position_for_user(
    supabase: Client,
    user: dict,
    market_id: str,
    side: str,
    size: float,
    exit_price: float,
    whale_wallet: str,
    trade: dict
) -> Optional[dict]:
    """Close an existing paper position (SELL) and calculate realized PnL"""
    user_id = user["id"]

    # Get user's open positions
    positions = await get_user_open_positions(supabase, user_id)
    position_key = f"{market_id}:{side}"

    if position_key not in positions:
        logger.info(f"No open {side} position for user {user_id[:8]} on {market_id[:8]} to close")
        return None

    position = positions[position_key]
    avg_entry_price = position["avg_entry_price"]
    open_size = position["total_size"]

    # Calculate how much we're closing (can't close more than we have)
    close_size = min(size, open_size)

    if close_size < 0.01:
        return None

    # Calculate realized PnL: (exit_price - entry_price) * size
    realized_pnl = (exit_price - avg_entry_price) * close_size

    # Create close trade record
    close_trade = {
        "user_id": user_id,
        "wallet_address": whale_wallet,
        "market_id": market_id,
        "market_title": trade.get("marketSlug", trade.get("question", f"Market {market_id[:8]}")),
        "wallet": whale_wallet,
        "wallet_alias": f"Whale {whale_wallet[:6]}",
        "side": side,
        "action": "SELL",
        "size": close_size,
        "price": exit_price,
        "executed": True,
        "is_closed": True,
        "pnl": round(realized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "entry_price": avg_entry_price,
        "timestamp": datetime.utcnow().isoformat(),
        "whale_trade_id": trade.get("id", trade.get("transactionHash", "")),
    }

    try:
        # Insert close trade
        supabase.table("trades").insert(close_trade).execute()

        # Mark original open trades as closed (proportionally)
        remaining_to_close = close_size
        for trade_id in position["trade_ids"]:
            if remaining_to_close <= 0:
                break

            # Get the original trade
            orig_resp = supabase.table("trades").select("*").eq("id", trade_id).single().execute()
            if orig_resp.data:
                orig_trade = orig_resp.data
                orig_size = float(orig_trade.get("size", 0))

                if orig_size <= remaining_to_close:
                    # Close entire trade
                    supabase.table("trades").update({
                        "is_closed": True,
                        "realized_pnl": round((exit_price - float(orig_trade.get("price", 0))) * orig_size, 2),
                        "exit_price": exit_price
                    }).eq("id", trade_id).execute()
                    remaining_to_close -= orig_size
                else:
                    # Partial close - update the size remaining
                    new_size = orig_size - remaining_to_close
                    supabase.table("trades").update({
                        "size": new_size
                    }).eq("id", trade_id).execute()
                    remaining_to_close = 0

        invalidate_position_cache(user_id)

        pnl_emoji = "💰" if realized_pnl >= 0 else "📉"
        logger.info(f"{pnl_emoji} CLOSE {side} for user {user_id[:8]}: ${close_size:.2f} @ ${exit_price:.2f} (entry: ${avg_entry_price:.2f}) | Realized P&L: ${realized_pnl:+.2f}")

        return close_trade

    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        return None


async def get_user_current_balance(supabase: Client, user: dict) -> float:
    """Calculate user's current available balance (starting - open positions cost + realized PnL)"""
    starting_balance = user.get("starting_balance", 1000)
    user_id = user["id"]

    # Get realized PnL from closed trades
    closed_response = supabase.table("trades").select("realized_pnl").eq(
        "user_id", user_id
    ).eq("is_closed", True).execute()

    realized_pnl = sum(t.get("realized_pnl", 0) or 0 for t in (closed_response.data or []))

    # Get cost of open positions (money currently in trades)
    open_response = supabase.table("trades").select("size, price").eq(
        "user_id", user_id
    ).eq("is_closed", False).eq("action", "BUY").execute()

    open_cost = sum((t.get("size", 0) or 0) * (t.get("price", 0) or 0) for t in (open_response.data or []))

    # Available balance = starting + realized - cost of open positions
    available_balance = starting_balance + realized_pnl - open_cost
    return available_balance


async def get_user_total_value(supabase: Client, user: dict) -> dict:
    """Calculate user's total portfolio value including unrealized PnL"""
    starting_balance = user.get("starting_balance", 1000)
    user_id = user["id"]

    # Get realized PnL from closed trades
    closed_response = supabase.table("trades").select("realized_pnl").eq(
        "user_id", user_id
    ).eq("is_closed", True).execute()

    realized_pnl = sum(t.get("realized_pnl", 0) or 0 for t in (closed_response.data or []))

    # Get unrealized PnL from open trades
    open_response = supabase.table("trades").select("pnl, size, price").eq(
        "user_id", user_id
    ).eq("is_closed", False).eq("action", "BUY").execute()

    unrealized_pnl = sum(t.get("pnl", 0) or 0 for t in (open_response.data or []))
    open_cost = sum((t.get("size", 0) or 0) * (t.get("price", 0) or 0) for t in (open_response.data or []))

    # Total value = starting + realized PnL + unrealized PnL
    total_value = starting_balance + realized_pnl + unrealized_pnl
    available_balance = starting_balance + realized_pnl - open_cost

    return {
        "starting_balance": starting_balance,
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(realized_pnl + unrealized_pnl, 2),
        "total_value": round(total_value, 2),
        "available_balance": round(available_balance, 2),
        "open_positions_cost": round(open_cost, 2)
    }


# =============================================================================
# AI SELL STRATEGY - Signal Collection (Phase 2)
# =============================================================================


async def fetch_market_metadata(market_id: str) -> Optional[dict]:
    """Fetch detailed market metadata including resolution date, volume, etc."""
    # Check cache (valid for 5 minutes)
    if market_id in market_metadata_cache:
        cached = market_metadata_cache[market_id]
        if datetime.utcnow() - cached.get("fetched_at", datetime.min) < timedelta(minutes=5):
            return cached

    async with httpx.AsyncClient() as client:
        try:
            # Use Gamma API for detailed market info
            response = await client.get(
                f"{GAMMA_API}/markets/{market_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()

                # Parse end date
                end_date_str = data.get("endDate") or data.get("endDateIso")
                end_date = None
                days_until_resolution = None
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        days_until_resolution = (end_date.replace(tzinfo=None) - datetime.utcnow()).days
                    except:
                        pass

                result = {
                    "market_id": market_id,
                    "question": data.get("question", ""),
                    "description": data.get("description", ""),
                    "end_date": end_date_str,
                    "days_until_resolution": days_until_resolution,
                    "volume": float(data.get("volume", 0)),
                    "volume_24h": float(data.get("volume24hr", 0)),
                    "liquidity": float(data.get("liquidity", 0)),
                    "closed": data.get("closed", False),
                    "resolved": data.get("resolved", False),
                    "outcome": data.get("outcome"),
                    "fetched_at": datetime.utcnow()
                }
                market_metadata_cache[market_id] = result
                return result
        except Exception as e:
            logger.debug(f"Failed to fetch market metadata for {market_id}: {e}")

    return None


async def fetch_whale_position(wallet_address: str, market_id: str) -> Optional[dict]:
    """Check if a whale is still holding a position in a specific market"""
    cache_key = f"{wallet_address}:{market_id}"

    # Check cache (valid for 2 minutes)
    if cache_key in whale_position_cache:
        cached = whale_position_cache[cache_key]
        if datetime.utcnow() - cached.get("fetched_at", datetime.min) < timedelta(minutes=2):
            return cached

    async with httpx.AsyncClient() as client:
        try:
            # Fetch wallet's recent trades in this market
            response = await client.get(
                f"{POLYMARKET_DATA_API}/trades",
                params={
                    "maker": wallet_address,
                    "market": market_id,
                    "limit": 100
                },
                timeout=10.0
            )
            if response.status_code == 200:
                trades = response.json() or []

                # Calculate net position from trades
                yes_size = 0.0
                no_size = 0.0
                latest_trade_time = None
                has_sold = False
                has_added = False

                for trade in trades:
                    side = trade.get("side", "").upper()
                    outcome = trade.get("outcome", "").lower()
                    size = float(trade.get("size", 0))

                    trade_time = trade.get("timestamp")
                    if trade_time and (latest_trade_time is None or trade_time > latest_trade_time):
                        latest_trade_time = trade_time

                    if side == "BUY":
                        if outcome == "yes":
                            yes_size += size
                        else:
                            no_size += size
                        has_added = True
                    elif side == "SELL":
                        if outcome == "yes":
                            yes_size -= size
                        else:
                            no_size -= size
                        has_sold = True

                result = {
                    "wallet": wallet_address,
                    "market_id": market_id,
                    "yes_position": max(0, yes_size),
                    "no_position": max(0, no_size),
                    "is_holding": yes_size > 0.01 or no_size > 0.01,
                    "has_sold_any": has_sold,
                    "has_added_more": has_added and (yes_size > 0 or no_size > 0),
                    "latest_trade_time": latest_trade_time,
                    "fetched_at": datetime.utcnow()
                }
                whale_position_cache[cache_key] = result
                return result

        except Exception as e:
            logger.debug(f"Failed to fetch whale position for {wallet_address[:10]} in {market_id[:10]}: {e}")

    return None


def calculate_volatility_score(price_history: list[float]) -> str:
    """Calculate volatility from price history (placeholder - uses simple range)"""
    if not price_history or len(price_history) < 2:
        return "unknown"

    price_range = max(price_history) - min(price_history)
    avg_price = sum(price_history) / len(price_history)

    if avg_price == 0:
        return "unknown"

    volatility_pct = (price_range / avg_price) * 100

    if volatility_pct > 20:
        return "high"
    elif volatility_pct > 10:
        return "medium"
    else:
        return "low"


async def collect_position_signals(
    supabase: Client,
    user_id: str,
    trade: dict,
    whale_wallet: str
) -> Optional[dict]:
    """
    Collect all signals needed for AI evaluation of a position.
    Returns a signals dict matching the ai_evaluations.signals schema.
    """
    market_id = trade.get("market_id", "")
    side = trade.get("side", "YES")
    entry_price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))

    # Get current market price
    market_data = await fetch_market_price(market_id)
    if not market_data:
        return None

    current_price = market_data.get("yes_price", 0.5) if side == "YES" else market_data.get("no_price", 0.5)

    # Calculate PnL percentage
    if entry_price > 0:
        pnl_percent = ((current_price - entry_price) / entry_price) * 100
    else:
        pnl_percent = 0

    # Calculate hold duration
    created_at = trade.get("created_at") or trade.get("timestamp")
    hold_hours = 0
    if created_at:
        try:
            if isinstance(created_at, str):
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_dt = datetime.fromtimestamp(created_at)
            hold_hours = (datetime.utcnow() - created_dt.replace(tzinfo=None)).total_seconds() / 3600
        except:
            pass

    # Get market metadata
    market_meta = await fetch_market_metadata(market_id)

    # Get whale position status
    whale_status = await fetch_whale_position(whale_wallet, market_id)

    # Build signals object
    signals = {
        # Position data
        "current_price": round(current_price, 4),
        "entry_price": round(entry_price, 4),
        "pnl_percent": round(pnl_percent, 2),
        "position_size": round(size, 2),
        "hold_hours": round(hold_hours, 1),
        "side": side,

        # Whale status
        "whale_status": "holding" if (whale_status and whale_status.get("is_holding")) else "unknown",
        "whale_has_sold": whale_status.get("has_sold_any", False) if whale_status else False,
        "whale_has_added": whale_status.get("has_added_more", False) if whale_status else False,

        # Market context
        "market_title": trade.get("market_title", market_meta.get("question", "") if market_meta else ""),
        "days_until_resolution": market_meta.get("days_until_resolution") if market_meta else None,
        "volume_24h": market_meta.get("volume_24h", 0) if market_meta else 0,
        "market_resolved": market_data.get("resolved", False),

        # Volatility (simplified for now)
        "volatility_score": "medium",  # TODO: Implement proper volatility calculation

        # Metadata
        "collected_at": datetime.utcnow().isoformat()
    }

    return signals


async def get_user_ai_settings(supabase: Client, user_id: str) -> dict:
    """Get user's AI configuration settings"""
    try:
        response = supabase.table("profiles").select(
            "ai_enabled, ai_risk_profile, ai_custom_instructions, confidence_threshold"
        ).eq("id", user_id).single().execute()

        if response.data:
            return {
                "ai_enabled": response.data.get("ai_enabled", True),
                "risk_profile": response.data.get("ai_risk_profile", "maximize_profit"),
                "custom_instructions": response.data.get("ai_custom_instructions", ""),
                "confidence_threshold": float(response.data.get("confidence_threshold", 0.7))
            }
    except Exception as e:
        logger.debug(f"Failed to get AI settings for user {user_id}: {e}")

    return {
        "ai_enabled": True,
        "risk_profile": "maximize_profit",
        "custom_instructions": "",
        "confidence_threshold": 0.7
    }


async def get_open_positions_for_ai_eval(supabase: Client, user_id: str) -> list[dict]:
    """Get all open positions for a user that need AI evaluation"""
    try:
        response = supabase.table("trades").select("*").eq(
            "user_id", user_id
        ).eq("is_closed", False).eq("action", "BUY").execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get open positions for user {user_id}: {e}")
        return []


# =============================================================================
# AI SELL STRATEGY - Decision Engine (Phase 3)
# =============================================================================


def build_ai_prompt(signals: dict, ai_settings: dict) -> str:
    """
    Build the prompt for Claude to evaluate a position.
    Returns a structured prompt with all signals and user preferences.
    """
    risk_profile = ai_settings.get("risk_profile", "maximize_profit")
    custom_instructions = ai_settings.get("custom_instructions", "")

    # Default thresholds based on risk profile
    thresholds = {
        "conservative": {"take_profit": 10, "stop_loss": -10},
        "moderate": {"take_profit": 15, "stop_loss": -15},
        "aggressive": {"take_profit": 25, "stop_loss": -20},
        "maximize_profit": {"take_profit": 20, "stop_loss": -15}
    }
    defaults = thresholds.get(risk_profile, thresholds["maximize_profit"])

    prompt = f"""You are a trading assistant for Polymarket prediction markets.

USER PROFILE:
- Risk preference: {risk_profile}
- Default thresholds: +{defaults['take_profit']}% take profit, {defaults['stop_loss']}% stop loss

CUSTOM INSTRUCTIONS (from user):
{custom_instructions if custom_instructions else "(none provided)"}

POSITION:
- Market: "{signals.get('market_title', 'Unknown market')}"
- Side: {signals.get('side', 'YES')}
- Entry price: ${signals.get('entry_price', 0):.4f}
- Current price: ${signals.get('current_price', 0):.4f}
- Unrealized PnL: {signals.get('pnl_percent', 0):+.1f}%
- Position size: ${signals.get('position_size', 0):.2f}
- Held for: {signals.get('hold_hours', 0):.1f} hours

WHALE STATUS:
- Whale still holding: {signals.get('whale_status', 'unknown').upper()}
- Whale has sold any: {'YES' if signals.get('whale_has_sold') else 'NO'}
- Whale added to position: {'YES' if signals.get('whale_has_added') else 'NO'}

MARKET CONTEXT:
- Days until resolution: {signals.get('days_until_resolution', 'Unknown')}
- 24h volume: ${signals.get('volume_24h', 0):,.0f}
- Volatility: {signals.get('volatility_score', 'unknown')}
- Market resolved: {'YES' if signals.get('market_resolved') else 'NO'}

DECISION REQUIRED:
Should we SELL or HOLD this position? Consider the user's risk preference and custom instructions.

You must respond with ONLY valid JSON in this exact format:
{{"action": "SELL" or "HOLD", "reasoning": "Brief explanation (1-2 sentences)", "confidence": 0.0 to 1.0, "strategy": "conservative" or "moderate" or "aggressive"}}

Respond with only the JSON, no other text."""

    return prompt


async def get_ai_decision(signals: dict, ai_settings: dict) -> Optional[dict]:
    """
    Call Claude API to get a sell/hold decision for a position.
    Returns dict with action, reasoning, confidence, strategy or None on error.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set, skipping AI decision")
        return None

    prompt = build_ai_prompt(signals, ai_settings)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Use Haiku for cost efficiency on routine evaluations
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Parse JSON response
        try:
            decision = json.loads(response_text)

            # Validate required fields
            if "action" not in decision or decision["action"] not in ["SELL", "HOLD"]:
                logger.warning(f"Invalid AI response action: {response_text}")
                return None

            # Ensure confidence is a float between 0 and 1
            confidence = float(decision.get("confidence", 0.5))
            decision["confidence"] = max(0.0, min(1.0, confidence))

            # Ensure strategy is valid
            if decision.get("strategy") not in ["conservative", "moderate", "aggressive"]:
                decision["strategy"] = ai_settings.get("risk_profile", "moderate")

            return decision

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON: {response_text}")
            return None

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return None
    except Exception as e:
        logger.error(f"AI decision error: {e}")
        return None


async def save_ai_evaluation(
    supabase: Client,
    user_id: str,
    trade_id: int,
    decision: dict,
    signals: dict
) -> bool:
    """Save an AI evaluation to the database for transparency and debugging"""
    try:
        evaluation = {
            "user_id": user_id,
            "trade_id": trade_id,
            "action": decision.get("action", "HOLD"),
            "reasoning": decision.get("reasoning", ""),
            "confidence": decision.get("confidence", 0.5),
            "signals": signals,
            "strategy_used": decision.get("strategy", "moderate")
        }

        supabase.table("ai_evaluations").insert(evaluation).execute()
        return True

    except Exception as e:
        logger.error(f"Failed to save AI evaluation: {e}")
        return False


async def execute_ai_sell(
    supabase: Client,
    user: dict,
    trade: dict,
    signals: dict,
    decision: dict
) -> Optional[dict]:
    """
    Execute a sell based on AI decision.
    Updates the trade as closed and records the AI reasoning.
    """
    user_id = user["id"]
    trade_id = trade.get("id")
    market_id = trade.get("market_id")
    side = trade.get("side", "YES")
    size = float(trade.get("size", 0))
    entry_price = float(trade.get("price", 0))
    current_price = signals.get("current_price", entry_price)

    # Calculate realized PnL
    realized_pnl = (current_price - entry_price) * size

    try:
        # Update the trade as closed with AI reasoning
        supabase.table("trades").update({
            "is_closed": True,
            "realized_pnl": round(realized_pnl, 2),
            "exit_price": current_price,
            "sell_reasoning": decision.get("reasoning", "AI decided to sell"),
            "ai_initiated": True
        }).eq("id", trade_id).execute()

        # Invalidate position cache
        invalidate_position_cache(user_id)

        # Create a SELL trade record
        sell_trade = {
            "user_id": user_id,
            "wallet_address": trade.get("wallet_address", ""),
            "market_id": market_id,
            "market_title": trade.get("market_title", ""),
            "wallet": trade.get("wallet", ""),
            "wallet_alias": trade.get("wallet_alias", ""),
            "side": side,
            "action": "SELL",
            "size": size,
            "price": current_price,
            "executed": True,
            "is_closed": True,
            "pnl": round(realized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "entry_price": entry_price,
            "exit_price": current_price,
            "sell_reasoning": decision.get("reasoning", ""),
            "ai_initiated": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        supabase.table("trades").insert(sell_trade).execute()

        pnl_emoji = "💰" if realized_pnl >= 0 else "📉"
        logger.info(
            f"🤖 {pnl_emoji} AI SELL for user {user_id[:8]}: "
            f"${size:.2f} @ ${current_price:.4f} | "
            f"PnL: ${realized_pnl:+.2f} | "
            f"Reason: {decision.get('reasoning', '')[:50]}"
        )

        return sell_trade

    except Exception as e:
        logger.error(f"Failed to execute AI sell: {e}")
        return None


# =============================================================================
# AI SELL STRATEGY - Adaptive Scheduling (Phase 4)
# =============================================================================


def calculate_eval_interval(signals: dict) -> int:
    """
    Calculate the next evaluation interval based on market conditions.
    Returns interval in seconds.

    Conditions that speed up evaluation:
    - High PnL (positive or negative) - position is moving
    - Close to resolution date - decisions become urgent
    - High volatility - market is active
    - Whale has sold - need to react quickly
    """
    base_interval = AI_EVAL_INTERVAL  # Default 5 minutes (300s)

    # Start with base interval
    interval = base_interval

    # Factor 1: PnL magnitude (bigger moves = faster checks)
    pnl_pct = abs(signals.get("pnl_percent", 0))
    if pnl_pct > 20:
        interval = min(interval, 60)   # Check every minute if >20% move
    elif pnl_pct > 10:
        interval = min(interval, 120)  # Check every 2 min if >10% move
    elif pnl_pct > 5:
        interval = min(interval, 180)  # Check every 3 min if >5% move

    # Factor 2: Days until resolution
    days_left = signals.get("days_until_resolution")
    if days_left is not None:
        if days_left <= 1:
            interval = min(interval, 60)   # Check every minute on last day
        elif days_left <= 3:
            interval = min(interval, 120)  # Check every 2 min in last 3 days
        elif days_left <= 7:
            interval = min(interval, 180)  # Check every 3 min in last week

    # Factor 3: Volatility
    volatility = signals.get("volatility_score", "medium")
    if volatility == "high":
        interval = min(interval, 120)

    # Factor 4: Whale sold
    if signals.get("whale_has_sold"):
        interval = min(interval, 60)  # Check every minute if whale sold

    # Never go below 30 seconds (rate limiting / cost control)
    return max(30, interval)


def should_evaluate_position(eval_key: str, signals: dict) -> bool:
    """
    Determine if a position should be evaluated now based on adaptive scheduling.
    """
    # Always evaluate if in urgent queue
    if eval_key in urgent_eval_queue:
        urgent_eval_queue.discard(eval_key)
        return True

    # Check if enough time has passed since last evaluation
    if eval_key not in last_ai_eval:
        return True  # Never evaluated before

    time_since_eval = (datetime.utcnow() - last_ai_eval[eval_key]).total_seconds()
    required_interval = calculate_eval_interval(signals)

    return time_since_eval >= required_interval


def flag_urgent_evaluation(user_id: str, trade_id: int, reason: str):
    """Flag a position for immediate AI evaluation"""
    eval_key = f"{user_id}:{trade_id}"
    urgent_eval_queue.add(eval_key)
    logger.info(f"⚡ Flagged position {trade_id} for urgent eval: {reason}")


async def check_for_urgent_conditions(supabase: Client):
    """
    Check open positions for conditions that require urgent evaluation:
    - Price moved >10% since last check
    - Whale sold their position
    Limited to 50 positions per cycle to avoid blocking the AI evaluation loop.
    """
    try:
        # Get recent open positions (limit to avoid blocking)
        response = supabase.table("trades").select(
            "id, user_id, market_id, wallet_address, price"
        ).eq("is_closed", False).eq("action", "BUY").order(
            "created_at", desc=True
        ).limit(50).execute()

        positions = response.data or []
        logger.info(f"🔍 Checking {len(positions)} positions for urgent conditions")

        for pos in positions:
            market_id = pos.get("market_id", "")
            trade_id = pos.get("id")
            user_id = pos.get("user_id")
            entry_price = float(pos.get("price", 0))
            wallet = pos.get("wallet_address", "")

            # Check for big price moves
            market_data = await fetch_market_price(market_id)
            if market_data:
                current_price = market_data.get("yes_price", 0.5)

                # Compare to previous cached price
                if market_id in previous_prices:
                    prev_price = previous_prices[market_id]
                    if prev_price > 0:
                        price_change_pct = abs((current_price - prev_price) / prev_price) * 100
                        if price_change_pct > 10:
                            flag_urgent_evaluation(
                                user_id, trade_id,
                                f"Price moved {price_change_pct:.1f}% since last check"
                            )

                previous_prices[market_id] = current_price

            # Check if whale sold
            if wallet:
                whale_pos = await fetch_whale_position(wallet, market_id)
                if whale_pos and whale_pos.get("has_sold_any") and not whale_pos.get("is_holding"):
                    flag_urgent_evaluation(
                        user_id, trade_id,
                        "Whale exited position"
                    )

        logger.info(f"🔍 Urgent conditions check complete")

    except Exception as e:
        logger.error(f"Error checking urgent conditions: {e}")


async def run_trading_cycle(supabase: Client):
    """Run one cycle of trade monitoring for all users"""
    try:
        # Get all active users
        users = await get_active_users(supabase)
        logger.info(f"Active users: {len(users)}")

        if not users:
            return

        # Collect all unique wallets being tracked
        all_wallets: dict[str, list[str]] = {}
        for user in users:
            user_wallets = await get_user_wallets(supabase, user["id"])
            for wallet in user_wallets:
                if wallet not in all_wallets:
                    all_wallets[wallet] = []
                all_wallets[wallet].append(user["id"])

        logger.info(f"Monitoring {len(all_wallets)} unique wallets")

        # Fetch trades from each wallet
        for wallet, user_ids in all_wallets.items():
            trades = await fetch_wallet_trades(wallet)

            if not trades:
                continue

            logger.info(f"Found {len(trades)} trades for wallet {wallet[:10]}...")

            # Process each trade for each user tracking this wallet
            for trade in trades:
                # Only process recent trades (last 30 minutes)
                trade_time = trade.get("timestamp", trade.get("createdAt", ""))
                if trade_time:
                    try:
                        if isinstance(trade_time, str):
                            trade_dt = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
                        else:
                            # Timestamp is in seconds (not milliseconds)
                            trade_dt = datetime.fromtimestamp(trade_time)

                        if datetime.utcnow() - trade_dt.replace(tzinfo=None) > timedelta(minutes=30):
                            continue
                    except:
                        pass

                # Find users tracking this wallet and execute paper trades
                for user in users:
                    if user["id"] in user_ids:
                        # Check minimum balance threshold
                        min_balance = user.get("min_account_balance", 0)
                        if min_balance > 0:
                            current_balance = await get_user_current_balance(supabase, user)
                            if current_balance <= min_balance:
                                logger.info(f"User {user['id'][:8]} below min balance (${current_balance:.2f} <= ${min_balance:.2f}), skipping trade")
                                continue

                        await process_trade_for_user(supabase, user, trade, wallet)

    except Exception as e:
        logger.error(f"Error in trading cycle: {e}")


async def pnl_update_loop(supabase: Client):
    """Continuously update PnL for all trades"""
    while True:
        try:
            await update_trade_pnl(supabase)
        except Exception as e:
            logger.error(f"PnL update error: {e}")

        await asyncio.sleep(PNL_UPDATE_INTERVAL)


# =============================================================================
# AI SELL STRATEGY - Evaluation Loop (Phase 3 integration point)
# =============================================================================


async def run_ai_evaluation_cycle(supabase: Client):
    """
    Run one cycle of AI position evaluation for all users with AI enabled.
    This collects signals for each open position and logs them.
    Phase 3 will add Claude API integration for actual sell decisions.
    """
    try:
        # Get all active users
        logger.info("🤖 Starting AI evaluation cycle...")
        users = await get_active_users(supabase)
        logger.info(f"🤖 Got {len(users)} active users")
        ai_enabled_users = [u for u in users if u.get("ai_enabled", True)]
        logger.info(f"🤖 {len(ai_enabled_users)} users have AI enabled")

        if not ai_enabled_users:
            logger.info("🤖 No AI-enabled users, skipping cycle")
            return

        logger.info(f"🤖 AI Evaluation: {len(ai_enabled_users)} users with AI enabled")

        total_positions = 0
        for user in ai_enabled_users:
            user_id = user["id"]

            # Get user's AI settings
            ai_settings = await get_user_ai_settings(supabase, user_id)
            if not ai_settings.get("ai_enabled"):
                continue

            # Get open positions
            positions = await get_open_positions_for_ai_eval(supabase, user_id)
            if not positions:
                continue

            # Get user's tracked wallets for whale status checks
            user_wallets = await get_user_wallets(supabase, user_id)

            for trade in positions:
                trade_id = trade.get("id")
                whale_wallet = trade.get("wallet_address", trade.get("wallet", ""))
                eval_key = f"{user_id}:{trade_id}"

                # Collect signals first (needed for adaptive scheduling)
                signals = await collect_position_signals(supabase, user_id, trade, whale_wallet)
                if not signals:
                    continue

                # Check if we should evaluate this position now (adaptive scheduling)
                if not should_evaluate_position(eval_key, signals):
                    continue

                total_positions += 1
                last_ai_eval[eval_key] = datetime.utcnow()

                # Log position info
                pnl_pct = signals.get("pnl_percent", 0)
                whale_status = signals.get("whale_status", "unknown")
                market_title = signals.get("market_title", "")[:30]

                logger.info(
                    f"  📊 Position {trade_id}: {market_title}... | "
                    f"PnL: {pnl_pct:+.1f}% | Whale: {whale_status}"
                )

                # Skip resolved markets (no decision needed)
                if signals.get("market_resolved"):
                    logger.info(f"    ⏭️ Market resolved, skipping AI evaluation")
                    continue

                # Get AI decision from Claude
                decision = await get_ai_decision(signals, ai_settings)

                if decision is None:
                    logger.debug(f"    ⚠️ No AI decision returned for position {trade_id}")
                    continue

                # Save the evaluation for transparency
                await save_ai_evaluation(supabase, user_id, trade_id, decision, signals)

                action = decision.get("action", "HOLD")
                confidence = decision.get("confidence", 0)
                reasoning = decision.get("reasoning", "")[:60]

                logger.info(
                    f"    🤖 AI Decision: {action} (confidence: {confidence:.0%}) - {reasoning}"
                )

                # Execute sell if AI is confident enough
                if action == "SELL" and confidence >= ai_settings.get("confidence_threshold", 0.7):
                    await execute_ai_sell(supabase, user, trade, signals, decision)

        if total_positions > 0:
            logger.info(f"🤖 AI Evaluation complete: {total_positions} positions analyzed")

    except Exception as e:
        logger.error(f"AI evaluation cycle error: {e}")


async def ai_evaluation_loop(supabase: Client):
    """Continuously run AI position evaluations with adaptive scheduling"""
    # Wait a bit before starting AI evaluations to let system stabilize
    await asyncio.sleep(30)

    logger.info(f"🤖 AI Evaluation loop started (base interval: {AI_EVAL_INTERVAL}s, adaptive)")

    while True:
        try:
            # Check for urgent conditions first (big price moves, whale exits)
            await check_for_urgent_conditions(supabase)

            # Run the evaluation cycle
            await run_ai_evaluation_cycle(supabase)
        except Exception as e:
            logger.error(f"AI evaluation loop error: {e}")

        # Run more frequently since individual positions use adaptive intervals
        await asyncio.sleep(60)  # Check every minute, but positions evaluated adaptively


async def main():
    """Main entry point"""
    logger.info("Starting PolyMind Multi-Tenant Bot Service")
    logger.info(f"Trade poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"PnL update interval: {PNL_UPDATE_INTERVAL} seconds")
    logger.info(f"AI evaluation interval: {AI_EVAL_INTERVAL} seconds")

    supabase = get_supabase()
    logger.info("Connected to Supabase")

    # Run all loops concurrently
    await asyncio.gather(
        trading_loop(supabase),
        pnl_update_loop(supabase),
        ai_evaluation_loop(supabase)
    )


async def trading_loop(supabase: Client):
    """Main trading loop"""
    while True:
        try:
            await run_trading_cycle(supabase)
        except Exception as e:
            logger.error(f"Cycle error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
