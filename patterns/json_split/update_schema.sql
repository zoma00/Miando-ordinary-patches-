-- Database schema updates for JSON split functionality
-- Run this SQL script in your PostgreSQL database

-- Add new JSONB columns to trading_snapshots table
ALTER TABLE trading_snapshots 
ADD COLUMN IF NOT EXISTS ohlc_all_json JSONB,
ADD COLUMN IF NOT EXISTS account_state_json JSONB,
ADD COLUMN IF NOT EXISTS open_trades_json JSONB,
ADD COLUMN IF NOT EXISTS closed_trades_json JSONB,
ADD COLUMN IF NOT EXISTS market_state_json JSONB;

-- Extra columns for ohlc_all calculations (max gain/loss analysis)
ALTER TABLE trading_snapshots 
ADD COLUMN IF NOT EXISTS max_gain_pct_1h DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS max_loss_pct_1h DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS calculation_range_minutes INT,
ADD COLUMN IF NOT EXISTS prediction_mode BOOLEAN DEFAULT FALSE;

-- Add index for performance on frequently queried columns
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_symbol_time 
ON trading_snapshots (symbol, snapshot_time);

-- Add index for max gain/loss calculations
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_gain_loss_calc
ON trading_snapshots (symbol, snapshot_time) 
WHERE max_gain_pct_1h IS NULL;

-- Create GIN indexes for JSON search performance
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_ohlc_json ON trading_snapshots USING GIN (ohlc_all_json);
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_account_json ON trading_snapshots USING GIN (account_state_json);
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_open_trades_json ON trading_snapshots USING GIN (open_trades_json);
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_closed_trades_json ON trading_snapshots USING GIN (closed_trades_json);
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_market_json ON trading_snapshots USING GIN (market_state_json);

-- Display the updated table structure
\d trading_snapshots;

-- Show sample usage
-- SELECT jsonb_pretty(ohlc_all_json) FROM trading_snapshots WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;
