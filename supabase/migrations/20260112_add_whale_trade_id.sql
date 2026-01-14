-- Add whale_trade_id column for tracking which whale trade triggered the copy trade
ALTER TABLE trades ADD COLUMN IF NOT EXISTS whale_trade_id TEXT;

-- Create index for faster lookups by whale trade ID
CREATE INDEX IF NOT EXISTS idx_trades_whale_trade_id ON trades(whale_trade_id);

COMMENT ON COLUMN trades.whale_trade_id IS 'ID of the original whale trade that triggered this copy trade';
