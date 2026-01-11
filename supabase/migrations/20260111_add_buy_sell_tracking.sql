-- Add columns for proper buy/sell tracking and realized PnL

-- Add action column to track BUY vs SELL
ALTER TABLE trades ADD COLUMN IF NOT EXISTS action TEXT DEFAULT 'BUY';

-- Add is_closed to track if position has been closed
ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_closed BOOLEAN DEFAULT FALSE;

-- Add realized_pnl for locked-in profits/losses
ALTER TABLE trades ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC DEFAULT 0;

-- Add entry_price for sell trades (to show what price we entered at)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_price NUMERIC;

-- Add exit_price for closed positions
ALTER TABLE trades ADD COLUMN IF NOT EXISTS exit_price NUMERIC;

-- Add current_price for live market price tracking
ALTER TABLE trades ADD COLUMN IF NOT EXISTS current_price NUMERIC;

-- Add is_resolved for market resolution tracking
ALTER TABLE trades ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN DEFAULT FALSE;

-- Update existing trades to have action = 'BUY' and is_closed = false
UPDATE trades SET action = 'BUY' WHERE action IS NULL;
UPDATE trades SET is_closed = FALSE WHERE is_closed IS NULL;

-- Create index for faster queries on open positions
CREATE INDEX IF NOT EXISTS idx_trades_open_positions
ON trades(user_id, is_closed, action)
WHERE is_closed = FALSE;

-- Create index for realized PnL queries
CREATE INDEX IF NOT EXISTS idx_trades_realized_pnl
ON trades(user_id, is_closed)
WHERE is_closed = TRUE;

COMMENT ON COLUMN trades.action IS 'BUY = opening position, SELL = closing position';
COMMENT ON COLUMN trades.is_closed IS 'Whether this position has been closed';
COMMENT ON COLUMN trades.realized_pnl IS 'Locked-in PnL when position was closed';
COMMENT ON COLUMN trades.entry_price IS 'Entry price (for SELL trades, shows the original entry)';
COMMENT ON COLUMN trades.exit_price IS 'Exit price when position was closed';
COMMENT ON COLUMN trades.current_price IS 'Current market price for unrealized PnL';
