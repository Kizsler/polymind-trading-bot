"""
PolyMind Multi-Tenant Bot Service
Runs on server, handles all users automatically
Includes real-time PnL calculation
"""
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
from supabase import create_client, Client

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

# Track processed trades to avoid duplicates
processed_trades: set[str] = set()
# Cache for market prices
market_price_cache: dict[str, dict] = {}


def get_supabase() -> Client:
    """Create Supabase client with service role key"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def get_active_users(supabase: Client) -> list[dict]:
    """Get all users with active (running) bots"""
    response = supabase.table("profiles").select("*").eq("bot_status", "running").execute()
    return response.data or []


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
    """Process a whale trade for a specific user (paper trading)"""
    user_id = user["id"]

    # Create unique trade ID
    trade_id = f"{user_id}:{trade.get('id', trade.get('transactionHash', ''))}"

    # Skip if already processed
    if trade_id in processed_trades:
        return None

    processed_trades.add(trade_id)

    # Calculate paper trade size based on user's copy_percentage
    copy_pct = user.get("copy_percentage", 0.1)
    whale_size = float(trade.get("size", trade.get("amount", 0)))
    our_size = whale_size * copy_pct

    # Get user's starting balance
    starting_balance = user.get("starting_balance", 1000)

    # Check if trade size is within limits (max 10% of starting balance per trade)
    max_trade_size = starting_balance * 0.1
    our_size = min(our_size, max_trade_size)

    if our_size < 1:  # Minimum trade size
        return None

    # Determine side
    side = trade.get("side", "BUY").upper()
    if side not in ["YES", "NO", "BUY", "SELL"]:
        side = "YES" if trade.get("outcome", "") == "Yes" else "NO"

    # Get market info
    market_id = trade.get("market", trade.get("conditionId", ""))
    entry_price = float(trade.get("price", 0.5))

    # Fetch current market price for initial PnL calculation
    market_data = await fetch_market_price(market_id)
    initial_pnl = 0.0
    current_price = entry_price

    if market_data:
        current_price = market_data.get("yes_price", entry_price) if side in ["YES", "BUY"] else market_data.get("no_price", entry_price)
        # Calculate initial unrealized PnL
        initial_pnl = (current_price - entry_price) * our_size

    # Create paper trade record (base fields that should always exist)
    paper_trade = {
        "user_id": user_id,
        "market_id": market_id,
        "market_title": trade.get("marketSlug", trade.get("question", f"Market {market_id[:8]}")),
        "wallet": whale_wallet,
        "wallet_alias": f"Whale {whale_wallet[:6]}",
        "side": "YES" if side in ["YES", "BUY"] else "NO",
        "size": our_size,
        "price": entry_price,
        "executed": True,
        "pnl": round(initial_pnl, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "whale_trade_id": trade.get("id", trade.get("transactionHash", "")),
    }

    # Save to Supabase
    try:
        # Try with new columns first
        full_trade = {**paper_trade, "current_price": current_price, "is_resolved": False}
        result = supabase.table("trades").insert(full_trade).execute()
        logger.info(f"Paper trade for user {user_id[:8]}: {paper_trade['side']} ${our_size:.2f} @ ${entry_price:.2f} on {market_id[:8]} (PnL: ${initial_pnl:.2f})")
        return paper_trade
    except Exception as e:
        # Fallback without new columns
        try:
            result = supabase.table("trades").insert(paper_trade).execute()
            logger.info(f"Paper trade for user {user_id[:8]}: {paper_trade['side']} ${our_size:.2f} @ ${entry_price:.2f} on {market_id[:8]} (PnL: ${initial_pnl:.2f})")
            return paper_trade
        except Exception as e2:
            logger.error(f"Failed to save trade: {e2}")
            return None


async def get_user_current_balance(supabase: Client, user: dict) -> float:
    """Calculate user's current balance (starting + realized PnL)"""
    starting_balance = user.get("starting_balance", 1000)

    # Get total PnL from executed trades
    response = supabase.table("trades").select("pnl").eq(
        "user_id", user["id"]
    ).eq("executed", True).execute()

    total_pnl = sum(t.get("pnl", 0) or 0 for t in (response.data or []))
    return starting_balance + total_pnl


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
                # Only process recent trades (last 5 minutes)
                trade_time = trade.get("timestamp", trade.get("createdAt", ""))
                if trade_time:
                    try:
                        if isinstance(trade_time, str):
                            trade_dt = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
                        else:
                            trade_dt = datetime.fromtimestamp(trade_time / 1000)

                        if datetime.utcnow() - trade_dt.replace(tzinfo=None) > timedelta(minutes=5):
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


async def main():
    """Main entry point"""
    logger.info("Starting PolyMind Multi-Tenant Bot Service")
    logger.info(f"Trade poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"PnL update interval: {PNL_UPDATE_INTERVAL} seconds")

    supabase = get_supabase()
    logger.info("Connected to Supabase")

    # Run both loops concurrently
    await asyncio.gather(
        trading_loop(supabase),
        pnl_update_loop(supabase)
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
