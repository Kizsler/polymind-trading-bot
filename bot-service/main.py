"""
PolyMind Multi-Tenant Bot Service
Runs on server, handles all users automatically
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
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # Service role key for server-side
POLYMARKET_DATA_API = "https://data-api.polymarket.com"
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))  # seconds

# Track processed trades to avoid duplicates
processed_trades: set[str] = set()


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

    return list(set(wallets))  # Dedupe


async def fetch_wallet_trades(wallet_address: str) -> list[dict]:
    """Fetch recent trades from a wallet via Polymarket Data API"""
    async with httpx.AsyncClient() as client:
        try:
            # Get trades from last hour
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
    price = float(trade.get("price", 0.5))

    # Create paper trade record
    paper_trade = {
        "user_id": user_id,
        "market_id": market_id,
        "market_title": trade.get("marketSlug", trade.get("question", f"Market {market_id[:8]}")),
        "wallet": whale_wallet,
        "wallet_alias": f"Whale {whale_wallet[:6]}",
        "side": "YES" if side in ["YES", "BUY"] else "NO",
        "size": our_size,
        "price": price,
        "executed": True,
        "pnl": 0,  # PnL calculated on close
        "timestamp": datetime.utcnow().isoformat(),
        "whale_trade_id": trade.get("id", trade.get("transactionHash", "")),
    }

    # Save to Supabase
    try:
        result = supabase.table("trades").insert(paper_trade).execute()
        logger.info(f"Paper trade for user {user_id[:8]}: {side} ${our_size:.2f} on {market_id[:8]}")
        return paper_trade
    except Exception as e:
        logger.error(f"Failed to save trade: {e}")
        return None


async def run_trading_cycle(supabase: Client):
    """Run one cycle of trade monitoring for all users"""
    try:
        # Get all active users
        users = await get_active_users(supabase)
        logger.info(f"Active users: {len(users)}")

        if not users:
            return

        # Collect all unique wallets being tracked
        all_wallets: dict[str, list[str]] = {}  # wallet -> [user_ids]
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
                        await process_trade_for_user(supabase, user, trade, wallet)

    except Exception as e:
        logger.error(f"Error in trading cycle: {e}")


async def main():
    """Main entry point"""
    logger.info("Starting PolyMind Multi-Tenant Bot Service")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")

    supabase = get_supabase()
    logger.info("Connected to Supabase")

    # Main loop
    while True:
        try:
            await run_trading_cycle(supabase)
        except Exception as e:
            logger.error(f"Cycle error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
